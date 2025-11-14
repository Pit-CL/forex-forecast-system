"""
Sistema de Deployment Autónomo con Docker y Scheduler
Gestiona la ejecución continua del sistema de forecasting
"""

import schedule
import time
import logging
import subprocess
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import requests
import psutil
import docker
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutonomousDeploymentManager:
    """
    Gestor de deployment completamente autónomo
    Maneja Docker, scheduling, monitoreo y auto-recovery
    """

    def __init__(self, config_file: str = "deployment_config.json"):
        self.config = self._load_config(config_file)
        self.docker_client = docker.from_env()
        self.containers = {}
        self.health_status = {}
        self.metrics_history = []

    def _load_config(self, config_file: str) -> Dict:
        """Carga configuración de deployment"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Configuración por defecto
            return {
                "horizons": {
                    "7d": {
                        "container_name": "forecast_7d",
                        "port": 8001,
                        "cpu_limit": "1.0",
                        "memory_limit": "1g",
                        "restart_policy": "on-failure",
                        "max_restarts": 3
                    },
                    "15d": {
                        "container_name": "forecast_15d",
                        "port": 8002,
                        "cpu_limit": "1.0",
                        "memory_limit": "1g",
                        "restart_policy": "on-failure",
                        "max_restarts": 3
                    },
                    "30d": {
                        "container_name": "forecast_30d",
                        "port": 8003,
                        "cpu_limit": "1.0",
                        "memory_limit": "1g",
                        "restart_policy": "on-failure",
                        "max_restarts": 3
                    },
                    "90d": {
                        "container_name": "forecast_90d",
                        "port": 8004,
                        "cpu_limit": "1.0",
                        "memory_limit": "1g",
                        "restart_policy": "on-failure",
                        "max_restarts": 3
                    }
                },
                "orchestrator": {
                    "container_name": "automl_orchestrator",
                    "port": 8000,
                    "cpu_limit": "2.0",
                    "memory_limit": "2g"
                },
                "monitoring": {
                    "prometheus_port": 9090,
                    "grafana_port": 3000,
                    "alert_manager_port": 9093
                },
                "schedule": {
                    "model_evaluation": "00:00",  # Medianoche
                    "data_update": "*/30",  # Cada 30 minutos
                    "health_check": "*/5",  # Cada 5 minutos
                    "backup": "03:00"  # 3 AM
                },
                "alerts": {
                    "email": "admin@forex-forecast.com",
                    "slack_webhook": "",
                    "error_threshold": 5,
                    "degradation_threshold": 0.1
                }
            }

    def setup_docker_environment(self) -> None:
        """Configura el ambiente Docker completo"""
        logger.info("Configurando ambiente Docker...")

        # Crear network si no existe
        try:
            self.docker_client.networks.get("forecast_network")
        except docker.errors.NotFound:
            self.docker_client.networks.create(
                "forecast_network",
                driver="bridge"
            )

        # Crear volúmenes para persistencia
        volumes = ["forecast_models", "forecast_data", "forecast_logs"]
        for volume_name in volumes:
            try:
                self.docker_client.volumes.get(volume_name)
            except docker.errors.NotFound:
                self.docker_client.volumes.create(volume_name)

        # Construir imágenes
        self._build_docker_images()

    def _build_docker_images(self) -> None:
        """Construye imágenes Docker para cada componente"""
        # Dockerfile para modelo de forecasting
        dockerfile_forecast = """
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    gcc g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY src/ ./src/
COPY models/ ./models/
COPY config/ ./config/

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Santiago

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Comando
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
        """

        # Dockerfile para orchestrator
        dockerfile_orchestrator = """
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    gcc g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements_orchestrator.txt .
RUN pip install --no-cache-dir -r requirements_orchestrator.txt

# Copiar código
COPY autonomous_system_architecture.py .
COPY config/ ./config/

# Variables de entorno
ENV PYTHONUNBUFFERED=1

# Comando
CMD ["python", "autonomous_system_architecture.py"]
        """

        # Guardar Dockerfiles
        with open("Dockerfile.forecast", "w") as f:
            f.write(dockerfile_forecast)

        with open("Dockerfile.orchestrator", "w") as f:
            f.write(dockerfile_orchestrator)

        # Construir imágenes
        logger.info("Construyendo imágenes Docker...")

        # Imagen para forecasting
        self.docker_client.images.build(
            path=".",
            dockerfile="Dockerfile.forecast",
            tag="forecast:latest",
            forcerm=True
        )

        # Imagen para orchestrator
        self.docker_client.images.build(
            path=".",
            dockerfile="Dockerfile.orchestrator",
            tag="orchestrator:latest",
            forcerm=True
        )

    def deploy_containers(self) -> None:
        """Despliega todos los contenedores"""
        logger.info("Desplegando contenedores...")

        # Desplegar orchestrator
        orchestrator_config = self.config['orchestrator']
        try:
            container = self.docker_client.containers.run(
                "orchestrator:latest",
                name=orchestrator_config['container_name'],
                ports={'8000/tcp': orchestrator_config['port']},
                environment={
                    'MODE': 'production',
                    'LOG_LEVEL': 'INFO'
                },
                volumes={
                    'forecast_models': {'bind': '/app/models', 'mode': 'rw'},
                    'forecast_data': {'bind': '/app/data', 'mode': 'rw'},
                    'forecast_logs': {'bind': '/app/logs', 'mode': 'rw'}
                },
                network="forecast_network",
                restart_policy={"Name": "unless-stopped"},
                detach=True,
                cpu_quota=int(float(orchestrator_config['cpu_limit']) * 100000),
                mem_limit=orchestrator_config['memory_limit']
            )
            self.containers['orchestrator'] = container
            logger.info(f"Orchestrator desplegado: {container.id[:12]}")

        except docker.errors.APIError as e:
            logger.error(f"Error desplegando orchestrator: {e}")

        # Desplegar contenedores de forecasting por horizonte
        for horizon, config in self.config['horizons'].items():
            try:
                container = self.docker_client.containers.run(
                    "forecast:latest",
                    name=config['container_name'],
                    ports={'8000/tcp': config['port']},
                    environment={
                        'HORIZON': horizon,
                        'MODE': 'production',
                        'ORCHESTRATOR_URL': f"http://orchestrator:8000"
                    },
                    volumes={
                        'forecast_models': {'bind': '/app/models', 'mode': 'ro'},
                        'forecast_data': {'bind': '/app/data', 'mode': 'ro'},
                        'forecast_logs': {'bind': '/app/logs', 'mode': 'rw'}
                    },
                    network="forecast_network",
                    restart_policy={
                        "Name": config['restart_policy'],
                        "MaximumRetryCount": config['max_restarts']
                    },
                    detach=True,
                    cpu_quota=int(float(config['cpu_limit']) * 100000),
                    mem_limit=config['memory_limit']
                )
                self.containers[horizon] = container
                logger.info(f"Container {horizon} desplegado: {container.id[:12]}")

            except docker.errors.APIError as e:
                logger.error(f"Error desplegando container {horizon}: {e}")

    def setup_monitoring(self) -> None:
        """Configura stack de monitoreo (Prometheus + Grafana)"""
        logger.info("Configurando monitoreo...")

        # Configuración de Prometheus
        prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'forecast_system'
    static_configs:
      - targets:
        - 'orchestrator:8000'
        - 'forecast_7d:8001'
        - 'forecast_15d:8002'
        - 'forecast_30d:8003'
        - 'forecast_90d:8004'
    metrics_path: '/metrics'
"""

        # Guardar configuración
        os.makedirs("monitoring", exist_ok=True)
        with open("monitoring/prometheus.yml", "w") as f:
            f.write(prometheus_config)

        # Desplegar Prometheus
        try:
            prometheus = self.docker_client.containers.run(
                "prom/prometheus:latest",
                name="prometheus",
                ports={'9090/tcp': self.config['monitoring']['prometheus_port']},
                volumes={
                    os.path.abspath("monitoring/prometheus.yml"): {
                        'bind': '/etc/prometheus/prometheus.yml',
                        'mode': 'ro'
                    }
                },
                network="forecast_network",
                restart_policy={"Name": "unless-stopped"},
                detach=True
            )
            self.containers['prometheus'] = prometheus
            logger.info(f"Prometheus desplegado: {prometheus.id[:12]}")

        except docker.errors.APIError as e:
            logger.error(f"Error desplegando Prometheus: {e}")

        # Desplegar Grafana
        try:
            grafana = self.docker_client.containers.run(
                "grafana/grafana:latest",
                name="grafana",
                ports={'3000/tcp': self.config['monitoring']['grafana_port']},
                environment={
                    'GF_SECURITY_ADMIN_PASSWORD': 'admin',
                    'GF_INSTALL_PLUGINS': 'grafana-clock-panel'
                },
                network="forecast_network",
                restart_policy={"Name": "unless-stopped"},
                detach=True
            )
            self.containers['grafana'] = grafana
            logger.info(f"Grafana desplegado: {grafana.id[:12]}")

        except docker.errors.APIError as e:
            logger.error(f"Error desplegando Grafana: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Verifica salud de todos los componentes"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'containers': {},
            'system': {},
            'alerts': []
        }

        # Verificar contenedores
        for name, container in self.containers.items():
            try:
                container.reload()
                status = container.status
                stats = container.stats(stream=False)

                # Calcular uso de recursos
                cpu_usage = self._calculate_cpu_usage(stats)
                memory_usage = self._calculate_memory_usage(stats)

                health_report['containers'][name] = {
                    'status': status,
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'restart_count': container.attrs['RestartCount']
                }

                # Alertas
                if status != 'running':
                    health_report['alerts'].append(
                        f"Container {name} no está running: {status}"
                    )

                if cpu_usage > 80:
                    health_report['alerts'].append(
                        f"Alto uso de CPU en {name}: {cpu_usage}%"
                    )

                if memory_usage > 80:
                    health_report['alerts'].append(
                        f"Alto uso de memoria en {name}: {memory_usage}%"
                    )

            except Exception as e:
                health_report['containers'][name] = {'error': str(e)}
                health_report['alerts'].append(f"Error verificando {name}: {e}")

        # Verificar sistema host
        health_report['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_connections': len(psutil.net_connections())
        }

        # Guardar estado de salud
        self.health_status = health_report

        return health_report

    def _calculate_cpu_usage(self, stats: Dict) -> float:
        """Calcula porcentaje de uso de CPU"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']

            if system_delta > 0:
                cpu_usage = (cpu_delta / system_delta) * 100.0
                return round(cpu_usage, 2)
        except (KeyError, TypeError, ZeroDivisionError):
            return 0.0

        return 0.0

    def _calculate_memory_usage(self, stats: Dict) -> float:
        """Calcula porcentaje de uso de memoria"""
        try:
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']

            if memory_limit > 0:
                percentage = (memory_usage / memory_limit) * 100.0
                return round(percentage, 2)
        except (KeyError, TypeError, ZeroDivisionError):
            return 0.0

        return 0.0

    def auto_scale(self) -> None:
        """Auto-escala recursos basado en carga"""
        logger.info("Evaluando necesidad de auto-scaling...")

        for name, container in self.containers.items():
            if name in self.health_status['containers']:
                container_health = self.health_status['containers'][name]

                # Si CPU > 90% por más de 5 minutos, aumentar límites
                if container_health.get('cpu_usage', 0) > 90:
                    logger.warning(f"Auto-scaling {name}: aumentando CPU limit")

                    # Actualizar container con nuevos límites
                    container.update(
                        cpu_quota=int(container.attrs['HostConfig']['CpuQuota'] * 1.5)
                    )

                # Si memoria > 90%, aumentar límite
                if container_health.get('memory_usage', 0) > 90:
                    logger.warning(f"Auto-scaling {name}: aumentando memoria")

                    # Calcular nuevo límite
                    current_limit = container.attrs['HostConfig']['Memory']
                    new_limit = int(current_limit * 1.5)

                    # Recrear container con nuevo límite (Docker no permite update de memoria)
                    self._recreate_container_with_new_limits(name, memory=new_limit)

    def _recreate_container_with_new_limits(self, container_name: str,
                                           **new_limits) -> None:
        """Recrea un container con nuevos límites de recursos"""
        try:
            container = self.containers[container_name]
            config = container.attrs['Config']
            host_config = container.attrs['HostConfig']

            # Detener container actual
            container.stop(timeout=10)
            container.remove()

            # Actualizar configuración
            if 'memory' in new_limits:
                host_config['Memory'] = new_limits['memory']

            if 'cpu' in new_limits:
                host_config['CpuQuota'] = new_limits['cpu']

            # Recrear container
            new_container = self.docker_client.containers.run(
                config['Image'],
                name=container_name,
                environment=config['Env'],
                ports=host_config['PortBindings'],
                volumes=host_config['Binds'],
                network=list(host_config['NetworkMode']),
                restart_policy=host_config['RestartPolicy'],
                detach=True,
                mem_limit=host_config.get('Memory'),
                cpu_quota=host_config.get('CpuQuota')
            )

            self.containers[container_name] = new_container
            logger.info(f"Container {container_name} recreado con nuevos límites")

        except Exception as e:
            logger.error(f"Error recreando container {container_name}: {e}")

    def backup_system(self) -> None:
        """Realiza backup completo del sistema"""
        logger.info("Iniciando backup del sistema...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        # Backup de modelos
        subprocess.run([
            "docker", "run", "--rm",
            "-v", "forecast_models:/models",
            "-v", f"{os.path.abspath(backup_dir)}:/backup",
            "alpine",
            "tar", "czf", "/backup/models.tar.gz", "/models"
        ])

        # Backup de datos
        subprocess.run([
            "docker", "run", "--rm",
            "-v", "forecast_data:/data",
            "-v", f"{os.path.abspath(backup_dir)}:/backup",
            "alpine",
            "tar", "czf", "/backup/data.tar.gz", "/data"
        ])

        # Backup de configuración
        subprocess.run([
            "cp", "-r", "config", f"{backup_dir}/config"
        ])

        logger.info(f"Backup completado en {backup_dir}")

        # Limpiar backups antiguos (mantener últimos 7)
        self._cleanup_old_backups()

    def _cleanup_old_backups(self, keep_last: int = 7) -> None:
        """Limpia backups antiguos"""
        backup_dirs = sorted([
            d for d in os.listdir("backups")
            if d.startswith("backup_")
        ])

        if len(backup_dirs) > keep_last:
            for old_backup in backup_dirs[:-keep_last]:
                backup_path = os.path.join("backups", old_backup)
                subprocess.run(["rm", "-rf", backup_path])
                logger.info(f"Backup antiguo eliminado: {old_backup}")

    def restore_from_backup(self, backup_timestamp: str) -> None:
        """Restaura sistema desde backup"""
        backup_dir = f"backups/backup_{backup_timestamp}"

        if not os.path.exists(backup_dir):
            logger.error(f"Backup no encontrado: {backup_dir}")
            return

        logger.info(f"Restaurando desde {backup_dir}")

        # Detener contenedores
        for container in self.containers.values():
            container.stop(timeout=10)

        # Restaurar modelos
        subprocess.run([
            "docker", "run", "--rm",
            "-v", "forecast_models:/models",
            "-v", f"{os.path.abspath(backup_dir)}:/backup",
            "alpine",
            "tar", "xzf", "/backup/models.tar.gz", "-C", "/"
        ])

        # Restaurar datos
        subprocess.run([
            "docker", "run", "--rm",
            "-v", "forecast_data:/data",
            "-v", f"{os.path.abspath(backup_dir)}:/backup",
            "alpine",
            "tar", "xzf", "/backup/data.tar.gz", "-C", "/"
        ])

        # Reiniciar contenedores
        self.deploy_containers()

        logger.info("Restauración completada")

    def send_alert(self, message: str, severity: str = "warning") -> None:
        """Envía alertas a los canales configurados"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'message': message,
            'system': 'autonomous_forecast'
        }

        # Email
        if self.config['alerts']['email']:
            # Implementar envío de email
            pass

        # Slack
        if self.config['alerts']['slack_webhook']:
            try:
                requests.post(
                    self.config['alerts']['slack_webhook'],
                    json={'text': f"[{severity.upper()}] {message}"}
                )
            except Exception as e:
                logger.error(f"Error enviando alerta a Slack: {e}")

        # Log
        logger.warning(f"ALERTA [{severity}]: {message}")

    def schedule_tasks(self) -> None:
        """Programa tareas automáticas"""
        logger.info("Configurando scheduler...")

        # Evaluación de modelos
        schedule.every().day.at(
            self.config['schedule']['model_evaluation']
        ).do(self.trigger_model_evaluation)

        # Actualización de datos
        schedule.every(30).minutes.do(self.update_data)

        # Health check
        schedule.every(5).minutes.do(self.health_check)

        # Backup
        schedule.every().day.at(
            self.config['schedule']['backup']
        ).do(self.backup_system)

        # Auto-scaling check
        schedule.every(10).minutes.do(self.auto_scale)

        logger.info("Scheduler configurado")

    def trigger_model_evaluation(self) -> None:
        """Dispara evaluación de modelos en orchestrator"""
        try:
            response = requests.post(
                f"http://localhost:{self.config['orchestrator']['port']}/evaluate",
                json={'trigger': 'scheduled'}
            )

            if response.status_code == 200:
                logger.info("Evaluación de modelos disparada")
            else:
                logger.error(f"Error en evaluación: {response.text}")

        except Exception as e:
            logger.error(f"Error disparando evaluación: {e}")

    def update_data(self) -> None:
        """Actualiza datos de mercado"""
        try:
            response = requests.post(
                f"http://localhost:{self.config['orchestrator']['port']}/update_data",
                json={'source': 'market_api'}
            )

            if response.status_code == 200:
                logger.info("Datos actualizados")
            else:
                logger.error(f"Error actualizando datos: {response.text}")

        except Exception as e:
            logger.error(f"Error actualizando datos: {e}")

    def run_autonomous_loop(self) -> None:
        """Loop principal de ejecución autónoma"""
        logger.info("="*60)
        logger.info("SISTEMA AUTÓNOMO DE FORECASTING INICIADO")
        logger.info("="*60)

        # Setup inicial
        self.setup_docker_environment()
        self.deploy_containers()
        self.setup_monitoring()
        self.schedule_tasks()

        # Loop infinito
        error_count = 0
        while True:
            try:
                # Ejecutar tareas programadas
                schedule.run_pending()

                # Verificar salud cada minuto
                if datetime.now().second == 0:
                    health = self.health_check()

                    # Enviar alertas si hay problemas
                    if health['alerts']:
                        for alert in health['alerts']:
                            self.send_alert(alert)

                    # Auto-recovery si hay errores críticos
                    critical_containers = [
                        name for name, status in health['containers'].items()
                        if status.get('status') != 'running'
                    ]

                    if critical_containers:
                        logger.warning(f"Containers críticos detectados: {critical_containers}")
                        for container_name in critical_containers:
                            self._restart_container(container_name)

                # Reset error count si todo está bien
                error_count = 0

                # Sleep
                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Deteniendo sistema autónomo...")
                break

            except Exception as e:
                error_count += 1
                logger.error(f"Error en loop principal: {e}")

                if error_count > self.config['alerts']['error_threshold']:
                    self.send_alert(
                        f"Sistema con errores críticos: {error_count} errores consecutivos",
                        severity="critical"
                    )

                    # Intentar auto-recovery completo
                    logger.info("Iniciando auto-recovery completo...")
                    self._full_system_recovery()
                    error_count = 0

                time.sleep(5)

        # Cleanup
        self._shutdown()

    def _restart_container(self, container_name: str) -> None:
        """Reinicia un container específico"""
        try:
            if container_name in self.containers:
                container = self.containers[container_name]
                container.restart(timeout=30)
                logger.info(f"Container {container_name} reiniciado")
        except Exception as e:
            logger.error(f"Error reiniciando {container_name}: {e}")

    def _full_system_recovery(self) -> None:
        """Recuperación completa del sistema"""
        logger.info("Ejecutando recuperación completa del sistema...")

        # 1. Detener todos los containers
        for container in self.containers.values():
            try:
                container.stop(timeout=10)
            except:
                pass

        # 2. Limpiar containers muertos
        subprocess.run(["docker", "container", "prune", "-f"])

        # 3. Re-desplegar
        self.deploy_containers()

        # 4. Verificar salud
        time.sleep(30)
        health = self.health_check()

        if health['alerts']:
            # Si sigue habiendo problemas, restaurar desde backup
            logger.warning("Problemas persisten, restaurando desde backup...")
            backups = sorted(os.listdir("backups"))
            if backups:
                latest_backup = backups[-1].replace("backup_", "")
                self.restore_from_backup(latest_backup)

    def _shutdown(self) -> None:
        """Apaga el sistema ordenadamente"""
        logger.info("Apagando sistema...")

        # Guardar estado
        state = {
            'shutdown_time': datetime.now().isoformat(),
            'containers': list(self.containers.keys()),
            'health_status': self.health_status
        }

        with open('shutdown_state.json', 'w') as f:
            json.dump(state, f, indent=2)

        # Detener containers
        for name, container in self.containers.items():
            try:
                container.stop(timeout=30)
                logger.info(f"Container {name} detenido")
            except Exception as e:
                logger.error(f"Error deteniendo {name}: {e}")

        logger.info("Sistema apagado correctamente")


# Script principal
if __name__ == "__main__":
    # Iniciar gestor de deployment
    manager = AutonomousDeploymentManager()

    # Ejecutar loop autónomo
    manager.run_autonomous_loop()