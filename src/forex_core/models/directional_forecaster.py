"""
Hybrid Directional-Magnitude Forecaster for USD/CLP

This module implements a hybrid approach to forex forecasting that combines:
1. A classifier for predicting price direction (up/down/neutral)
2. A regressor for predicting magnitude (how much the price will change)

The key innovation is separating the direction prediction from magnitude prediction,
which improves directional accuracy - critical for trading decisions.

Author: ML Expert Agent
Date: 2025-11-14
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit


@dataclass
class DirectionalForecast:
    """
    Container for directional forecast results.

    Attributes:
        direction: Predicted direction (-1=down, 0=neutral, +1=up)
        direction_proba: Confidence in the predicted direction (0.0 to 1.0)
        magnitude: Predicted absolute change amount in CLP
        combined_forecast: Final forecast value combining direction and magnitude
        confidence_level: Overall confidence level ('high', 'medium', 'low')
    """
    direction: int  # -1 (down), 0 (neutral), +1 (up)
    direction_proba: float  # Confidence in direction
    magnitude: float  # Predicted change amount
    combined_forecast: float  # direction * magnitude + current_price
    confidence_level: str = "medium"  # 'high', 'medium', 'low'

    def to_dict(self) -> Dict[str, Any]:
        """Convert forecast to dictionary."""
        return {
            "direction": self.direction,
            "direction_proba": self.direction_proba,
            "magnitude": self.magnitude,
            "combined_forecast": self.combined_forecast,
            "confidence_level": self.confidence_level,
        }


class DirectionalForecaster:
    """
    Hybrid model for forex forecasting: Classification for direction + Regression for magnitude.

    This approach improves directional accuracy from ~50% to target >58% by:
    1. Using specialized features for direction prediction (momentum, trend strength)
    2. Training a dedicated classifier optimized for directional accuracy
    3. Combining with magnitude predictions from existing XGBoost models

    The classifier uses GradientBoosting by default but can be configured to use
    RandomForest or other ensemble methods.

    Attributes:
        neutral_threshold: Threshold for considering a change as neutral (default: 0.5%)
        classifier: The direction classifier model
        magnitude_model: The magnitude prediction model (typically XGBoost)
        directional_features: List of features specifically for direction prediction
        is_fitted: Whether the classifier has been trained
    """

    def __init__(
        self,
        neutral_threshold: float = 0.005,
        classifier_type: str = "gradient_boosting",
        random_state: int = 42
    ):
        """
        Initialize the directional forecaster.

        Args:
            neutral_threshold: Changes < this % considered neutral (0.005 = 0.5% = ~5 CLP)
            classifier_type: Type of classifier ('gradient_boosting' or 'random_forest')
            random_state: Random state for reproducibility
        """
        self.neutral_threshold = neutral_threshold
        self.classifier_type = classifier_type
        self.random_state = random_state

        # Initialize classifier based on type
        if classifier_type == "gradient_boosting":
            self.classifier = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                min_samples_split=10,
                min_samples_leaf=5,
                subsample=0.8,
                random_state=random_state
            )
        elif classifier_type == "random_forest":
            self.classifier = RandomForestClassifier(
                n_estimators=200,
                max_depth=7,
                min_samples_split=10,
                min_samples_leaf=5,
                class_weight='balanced',  # Handle class imbalance
                random_state=random_state,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown classifier type: {classifier_type}")

        self.magnitude_model = None  # Will be set externally
        self.directional_features: List[str] = []
        self.is_fitted = False
        self.feature_importance_: Optional[pd.DataFrame] = None
        self.training_metrics_: Dict[str, Any] = {}

    def add_directional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add momentum and trend features optimized for direction prediction.

        These features are specifically designed to capture directional patterns:
        - Multi-timeframe momentum indicators
        - Trend strength and acceleration
        - Rate of change indicators
        - Volatility-adjusted momentum
        - Cross-asset divergences (if available)

        Args:
            df: DataFrame with at least 'usdclp' column

        Returns:
            DataFrame with additional directional features
        """
        df = df.copy()

        # Price momentum (multiple timeframes for better signal)
        df['momentum_3d'] = df['usdclp'].pct_change(3)
        df['momentum_5d'] = df['usdclp'].pct_change(5)
        df['momentum_7d'] = df['usdclp'].pct_change(7)
        df['momentum_10d'] = df['usdclp'].pct_change(10)
        df['momentum_14d'] = df['usdclp'].pct_change(14)
        df['momentum_21d'] = df['usdclp'].pct_change(21)

        # Acceleration (rate of change of momentum - captures turning points)
        df['acceleration_3d'] = df['momentum_3d'].diff()
        df['acceleration_7d'] = df['momentum_7d'].diff()
        df['acceleration_14d'] = df['momentum_14d'].diff()

        # Trend strength indicators
        df['trend_strength'] = self._calculate_adx(df['usdclp'], period=14)
        df['trend_strength_7d'] = self._calculate_adx(df['usdclp'], period=7)

        # Moving average convergence
        df['sma_5'] = df['usdclp'].rolling(5).mean()
        df['sma_10'] = df['usdclp'].rolling(10).mean()
        df['sma_20'] = df['usdclp'].rolling(20).mean()
        df['ma_convergence_5_10'] = (df['sma_5'] - df['sma_10']) / df['sma_10']
        df['ma_convergence_10_20'] = (df['sma_10'] - df['sma_20']) / df['sma_20']

        # Price position relative to moving averages
        df['price_vs_sma5'] = (df['usdclp'] - df['sma_5']) / df['sma_5']
        df['price_vs_sma20'] = (df['usdclp'] - df['sma_20']) / df['sma_20']

        # Volatility metrics
        df['volatility_7d'] = df['usdclp'].rolling(7).std() / df['usdclp'].rolling(7).mean()
        df['volatility_20d'] = df['usdclp'].rolling(20).std() / df['usdclp'].rolling(20).mean()

        # Volatility-adjusted momentum (momentum relative to volatility)
        df['vol_adj_momentum_7d'] = df['momentum_7d'] / (df['volatility_7d'] + 1e-8)
        df['vol_adj_momentum_14d'] = df['momentum_14d'] / (df['volatility_20d'] + 1e-8)

        # RSI (Relative Strength Index) - momentum oscillator
        df['rsi_7d'] = self._calculate_rsi(df['usdclp'], period=7)
        df['rsi_14d'] = self._calculate_rsi(df['usdclp'], period=14)

        # Copper momentum (leading indicator for CLP)
        if 'copper_price' in df.columns:
            df['copper_momentum_3d'] = df['copper_price'].pct_change(3)
            df['copper_momentum_7d'] = df['copper_price'].pct_change(7)
            df['copper_momentum_14d'] = df['copper_price'].pct_change(14)

            # USD/CLP vs Copper divergence (when they move in opposite directions)
            df['usdclp_copper_divergence_3d'] = df['momentum_3d'] - df['copper_momentum_3d']
            df['usdclp_copper_divergence_7d'] = df['momentum_7d'] - df['copper_momentum_7d']

        # DXY momentum (USD strength indicator)
        if 'dxy' in df.columns:
            df['dxy_momentum_3d'] = df['dxy'].pct_change(3)
            df['dxy_momentum_7d'] = df['dxy'].pct_change(7)
            df['dxy_momentum_14d'] = df['dxy'].pct_change(14)

            # USD/CLP vs DXY correlation
            df['usdclp_dxy_correlation_7d'] = (
                df['usdclp'].rolling(7).corr(df['dxy'])
            )

        # VIX changes (risk sentiment)
        if 'vix' in df.columns:
            df['vix_change_3d'] = df['vix'].pct_change(3)
            df['vix_change_7d'] = df['vix'].pct_change(7)
            df['vix_level'] = df['vix']  # Absolute VIX level

        # Store feature names for later use
        self.directional_features = [
            col for col in df.columns
            if col not in ['usdclp', 'date'] and
            any(indicator in col for indicator in [
                'momentum', 'acceleration', 'trend', 'ma_', 'volatility',
                'vol_adj', 'rsi', 'divergence', 'correlation', 'vix'
            ])
        ]

        logger.info(f"Added {len(self.directional_features)} directional features")

        return df

    def create_direction_labels(
        self,
        df: pd.DataFrame,
        horizon: int = 7,
        target_col: str = 'usdclp'
    ) -> pd.Series:
        """
        Create directional labels for training.

        Labels are created based on future price changes:
        - -1: Price decreases by more than neutral_threshold
        - 0: Price change within neutral_threshold
        - +1: Price increases by more than neutral_threshold

        Args:
            df: DataFrame with target column
            horizon: Days ahead to predict
            target_col: Name of the target column

        Returns:
            Series with direction labels (-1, 0, +1)
        """
        # Calculate future return
        future_price = df[target_col].shift(-horizon)
        current_price = df[target_col]
        future_return = (future_price / current_price) - 1

        # Create labels based on threshold
        labels = pd.Series(0, index=df.index, name='direction')  # Default: neutral

        # Up movement (positive return > threshold)
        labels[future_return > self.neutral_threshold] = 1

        # Down movement (negative return < -threshold)
        labels[future_return < -self.neutral_threshold] = -1

        # Log class distribution
        distribution = labels.value_counts().sort_index()
        total = len(labels.dropna())

        if total > 0:
            logger.info(
                f"Direction labels (horizon={horizon}d, threshold={self.neutral_threshold:.1%}):\n"
                f"  Down (-1): {distribution.get(-1, 0)} ({distribution.get(-1, 0)/total:.1%})\n"
                f"  Neutral (0): {distribution.get(0, 0)} ({distribution.get(0, 0)/total:.1%})\n"
                f"  Up (+1): {distribution.get(1, 0)} ({distribution.get(1, 0)/total:.1%})"
            )

        return labels

    def train_direction_classifier(
        self,
        X: pd.DataFrame,
        y_direction: pd.Series,
        validation_split: float = 0.2,
        use_time_series_cv: bool = True
    ) -> Dict[str, Any]:
        """
        Train the direction classifier.

        Args:
            X: Feature matrix (should include directional features)
            y_direction: Direction labels (-1, 0, +1)
            validation_split: Fraction of data to use for validation
            use_time_series_cv: Whether to use time series cross-validation

        Returns:
            Dictionary with training metrics
        """
        # Remove any NaN values
        mask = ~(X.isna().any(axis=1) | y_direction.isna())
        X_clean = X[mask]
        y_clean = y_direction[mask]

        if len(X_clean) < 100:
            raise ValueError(f"Insufficient training data: {len(X_clean)} samples")

        # Split data for validation
        if use_time_series_cv:
            # Time series cross-validation
            tscv = TimeSeriesSplit(n_splits=3)
            accuracies = []
            reports = []

            for train_idx, val_idx in tscv.split(X_clean):
                X_train, X_val = X_clean.iloc[train_idx], X_clean.iloc[val_idx]
                y_train, y_val = y_clean.iloc[train_idx], y_clean.iloc[val_idx]

                self.classifier.fit(X_train, y_train)
                y_pred = self.classifier.predict(X_val)

                accuracies.append(accuracy_score(y_val, y_pred))
                reports.append(classification_report(y_val, y_pred, output_dict=True))

            # Final training on all data
            self.classifier.fit(X_clean, y_clean)

            # Average metrics
            avg_accuracy = np.mean(accuracies)
            logger.info(f"Average CV directional accuracy: {avg_accuracy:.2%}")

        else:
            # Simple train/validation split
            split_idx = int(len(X_clean) * (1 - validation_split))
            X_train = X_clean.iloc[:split_idx]
            y_train = y_clean.iloc[:split_idx]
            X_val = X_clean.iloc[split_idx:]
            y_val = y_clean.iloc[split_idx:]

            # Train classifier
            self.classifier.fit(X_train, y_train)

            # Validate
            y_pred = self.classifier.predict(X_val)
            avg_accuracy = accuracy_score(y_val, y_pred)

            # Confusion matrix
            cm = confusion_matrix(y_val, y_pred, labels=[-1, 0, 1])
            logger.info(f"Confusion Matrix:\n{cm}")

            # Classification report
            report = classification_report(y_val, y_pred, target_names=['Down', 'Neutral', 'Up'])
            logger.info(f"Classification Report:\n{report}")

        # Extract and store feature importance
        if hasattr(self.classifier, 'feature_importances_'):
            self.feature_importance_ = pd.DataFrame({
                'feature': X_clean.columns,
                'importance': self.classifier.feature_importances_
            }).sort_values('importance', ascending=False)

            logger.info(f"Top 10 directional features:\n{self.feature_importance_.head(10)}")

        # Store training metrics
        self.training_metrics_ = {
            'accuracy': avg_accuracy,
            'n_samples': len(X_clean),
            'n_features': X_clean.shape[1],
            'classifier_type': self.classifier_type,
        }

        self.is_fitted = True

        return self.training_metrics_

    def predict(
        self,
        X: pd.DataFrame,
        magnitude_model: Any,
        current_price: float,
        return_proba: bool = False
    ) -> DirectionalForecast:
        """
        Make hybrid directional-magnitude forecast.

        Args:
            X: Feature matrix for single prediction (1 row)
            magnitude_model: Trained regressor for magnitude prediction
            current_price: Current USD/CLP rate
            return_proba: Whether to return probability distribution

        Returns:
            DirectionalForecast with direction, magnitude, and combined forecast

        Raises:
            ValueError: If classifier not fitted
        """
        if not self.is_fitted:
            raise ValueError("Classifier must be trained before prediction. Call train_direction_classifier first.")

        # Ensure X is 2D
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        elif isinstance(X, pd.DataFrame) and len(X) == 1:
            pass  # Already in correct format
        else:
            X = X.iloc[0:1]  # Take first row if multiple

        # Predict direction and probability
        direction_proba = self.classifier.predict_proba(X)[0]

        # Map probabilities to classes (-1, 0, 1)
        classes = self.classifier.classes_
        direction_idx = np.argmax(direction_proba)
        direction = classes[direction_idx]
        confidence = direction_proba[direction_idx]

        # Determine confidence level
        if confidence > 0.7:
            confidence_level = "high"
        elif confidence > 0.5:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        # Predict magnitude using the regression model
        if magnitude_model is not None:
            magnitude_pred = magnitude_model.predict(X)[0]
            # Calculate absolute change
            magnitude = abs(magnitude_pred - current_price)
        else:
            # Fallback: use historical average change
            magnitude = current_price * 0.01  # 1% change as default

        # Combine direction and magnitude
        if direction == 0:  # Neutral
            combined = current_price  # No significant change expected
        else:
            # Apply direction to magnitude
            combined = current_price + (direction * magnitude)

        # Create forecast object
        forecast = DirectionalForecast(
            direction=int(direction),
            direction_proba=float(confidence),
            magnitude=float(magnitude),
            combined_forecast=float(combined),
            confidence_level=confidence_level
        )

        # Log prediction details
        logger.debug(
            f"Directional forecast: direction={direction} ({confidence:.2%}), "
            f"magnitude={magnitude:.2f}, combined={combined:.2f}"
        )

        if return_proba:
            # Add probability distribution to forecast
            forecast.proba_distribution = {
                int(classes[i]): float(direction_proba[i])
                for i in range(len(classes))
            }

        return forecast

    def evaluate_directional_accuracy(
        self,
        y_true: pd.Series,
        y_pred: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate directional accuracy metrics.

        Args:
            y_true: True directions
            y_pred: Predicted directions

        Returns:
            Dictionary with accuracy metrics
        """
        # Overall accuracy
        accuracy = accuracy_score(y_true, y_pred)

        # Directional accuracy (excluding neutral)
        mask_non_neutral = (y_true != 0) & (y_pred != 0)
        if mask_non_neutral.sum() > 0:
            directional_accuracy = (
                (y_true[mask_non_neutral] * y_pred[mask_non_neutral] > 0).mean()
            )
        else:
            directional_accuracy = 0.0

        # Up/Down specific accuracy
        up_mask = y_true == 1
        down_mask = y_true == -1

        up_accuracy = accuracy_score(y_true[up_mask], y_pred[up_mask]) if up_mask.sum() > 0 else 0.0
        down_accuracy = accuracy_score(y_true[down_mask], y_pred[down_mask]) if down_mask.sum() > 0 else 0.0

        return {
            'overall_accuracy': accuracy,
            'directional_accuracy': directional_accuracy,
            'up_accuracy': up_accuracy,
            'down_accuracy': down_accuracy,
        }

    @staticmethod
    def _calculate_adx(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX) for trend strength.

        ADX measures the strength of a trend, regardless of direction.
        Values > 25 indicate a strong trend.

        Args:
            prices: Price series
            period: Lookback period

        Returns:
            ADX values
        """
        # Calculate price changes
        high = prices.rolling(2).max()
        low = prices.rolling(2).min()

        # Directional movements
        plus_dm = high.diff().clip(lower=0)
        minus_dm = -low.diff().clip(upper=0)

        # True range
        tr = high - low

        # Average true range
        atr = tr.rolling(period).mean()

        # Directional indicators
        plus_di = 100 * (plus_dm.rolling(period).mean() / (atr + 1e-8))
        minus_di = 100 * (minus_dm.rolling(period).mean() / (atr + 1e-8))

        # Directional index
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)

        # Average directional index
        adx = dx.rolling(period).mean()

        return adx

    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI is a momentum oscillator that measures the speed and magnitude of price changes.
        Values > 70 indicate overbought, < 30 indicate oversold.

        Args:
            prices: Price series
            period: Lookback period

        Returns:
            RSI values
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        # Calculate average gains and losses
        avg_gains = gains.rolling(period).mean()
        avg_losses = losses.rolling(period).mean()

        # Calculate RS and RSI
        rs = avg_gains / (avg_losses + 1e-8)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def save(self, filepath: str):
        """
        Save the trained directional forecaster.

        Args:
            filepath: Path to save the model
        """
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted DirectionalForecaster")

        joblib.dump(self, filepath)
        logger.info(f"DirectionalForecaster saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'DirectionalForecaster':
        """
        Load a trained directional forecaster.

        Args:
            filepath: Path to load from

        Returns:
            Loaded DirectionalForecaster instance
        """
        forecaster = joblib.load(filepath)
        if not isinstance(forecaster, cls):
            raise ValueError(f"Loaded object is not a DirectionalForecaster: {type(forecaster)}")

        logger.info(f"DirectionalForecaster loaded from {filepath}")
        return forecaster

    def __repr__(self) -> str:
        """String representation."""
        status = "fitted" if self.is_fitted else "not fitted"
        return (
            f"DirectionalForecaster(classifier={self.classifier_type}, "
            f"neutral_threshold={self.neutral_threshold:.1%}, "
            f"status={status})"
        )