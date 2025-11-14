"""
Feature Selection for USD/CLP Forecasting

This module implements automated feature selection to reduce overfitting and improve
model generalization. It reduces features from 58+ to ~30 using a multi-stage approach:

1. Correlation analysis (remove |r| > 0.95)
2. LASSO regression for feature importance
3. Recursive Feature Elimination (RFE) with RandomForest

The selection process ensures that only the most informative and non-redundant features
are retained, improving model stability and reducing the risk of overfitting.

Author: ML Expert Agent
Date: 2025-11-14
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFE
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler


class FeatureSelector:
    """
    Automated feature selection for USD/CLP forecasting models.

    This class implements a 3-stage feature selection pipeline:
    1. Remove highly correlated features (multicollinearity reduction)
    2. LASSO-based selection (L1 regularization)
    3. Recursive Feature Elimination with RandomForest (non-linear relationships)

    Attributes:
        target_features: Target number of features to select (default: 30)
        correlation_threshold: Maximum allowed correlation between features (default: 0.95)
        selected_features: List of selected feature names after fitting
        feature_importance_: Feature importance scores from the selection process
    """

    def __init__(
        self,
        target_features: int = 30,
        correlation_threshold: float = 0.95,
        random_state: int = 42
    ):
        """
        Initialize the feature selector.

        Args:
            target_features: Target number of features to select (should be < original features)
            correlation_threshold: Threshold for removing correlated features (0.0 to 1.0)
            random_state: Random state for reproducibility
        """
        self.target_features = target_features
        self.correlation_threshold = correlation_threshold
        self.random_state = random_state
        self.selected_features: List[str] = []
        self.feature_importance_: Optional[pd.DataFrame] = None
        self.scaler = StandardScaler()
        self._is_fitted = False

    def fit_select(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Select optimal features using the 3-stage process.

        This method performs feature selection by:
        1. Removing highly correlated features
        2. Applying LASSO regression for initial selection
        3. Using RFE with RandomForest for final selection

        Args:
            X: Feature matrix (58+ features)
            y: Target variable (usdclp future values)
            verbose: Whether to log progress information

        Returns:
            X_selected: Reduced feature matrix (~30 features)

        Raises:
            ValueError: If X has fewer features than target_features
        """
        if verbose:
            logger.info(f"Starting feature selection: {len(X.columns)} initial features")

        # Validate inputs
        if len(X.columns) <= self.target_features:
            logger.warning(
                f"Input has {len(X.columns)} features, which is <= target {self.target_features}. "
                "Returning all features."
            )
            self.selected_features = list(X.columns)
            self._is_fitted = True
            return X

        # Store original feature names
        original_features = list(X.columns)

        # Stage 1: Remove highly correlated features
        X_stage1 = self._remove_correlated_features(X.copy(), verbose=verbose)
        if verbose:
            logger.info(f"After correlation filter: {len(X_stage1.columns)} features remain")

        # Stage 2: LASSO-based selection
        X_stage2 = self._lasso_selection(X_stage1.copy(), y, verbose=verbose)
        if verbose:
            logger.info(f"After LASSO selection: {len(X_stage2.columns)} features remain")

        # Stage 3: RFE with RandomForest (only if still above target)
        if len(X_stage2.columns) > self.target_features:
            X_final = self._rfe_selection(X_stage2.copy(), y, verbose=verbose)
        else:
            X_final = X_stage2

        if verbose:
            logger.info(f"Final feature set: {len(X_final.columns)} features selected")
            logger.info(f"Selected features: {list(X_final.columns)[:10]}...")  # Show first 10

        # Store selected features and calculate importance
        self.selected_features = list(X_final.columns)
        self._calculate_feature_importance(X_final, y)
        self._is_fitted = True

        return X_final

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Apply learned feature selection to new data.

        Args:
            X: Feature matrix with original features

        Returns:
            X_selected: Matrix with only selected features

        Raises:
            ValueError: If selector has not been fitted
            KeyError: If required features are missing from X
        """
        if not self._is_fitted:
            raise ValueError("FeatureSelector must be fitted before transform. Call fit_select first.")

        # Check if all selected features are present
        missing_features = set(self.selected_features) - set(X.columns)
        if missing_features:
            raise KeyError(f"Missing required features: {missing_features}")

        return X[self.selected_features]

    def fit_transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Fit selector and transform data in one step.

        Args:
            X: Feature matrix
            y: Target variable
            verbose: Whether to log progress

        Returns:
            X_selected: Transformed feature matrix
        """
        return self.fit_select(X, y, verbose=verbose)

    def _remove_correlated_features(
        self,
        X: pd.DataFrame,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Remove features with correlation > threshold.

        This method removes one feature from each highly correlated pair,
        keeping the feature that appears first in the DataFrame.

        Args:
            X: Feature matrix
            verbose: Whether to log progress

        Returns:
            X_filtered: DataFrame with correlated features removed
        """
        # Calculate correlation matrix
        corr_matrix = X.corr().abs()

        # Create upper triangle matrix
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # Find features to drop
        to_drop = set()
        for column in upper_triangle.columns:
            # Find features correlated with this column
            correlated_features = upper_triangle.index[
                upper_triangle[column] > self.correlation_threshold
            ].tolist()

            # Add to drop list
            to_drop.update(correlated_features)

        if verbose and to_drop:
            logger.info(f"Removing {len(to_drop)} correlated features: {list(to_drop)[:5]}...")

        # Drop correlated features
        return X.drop(columns=list(to_drop))

    def _lasso_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Select features using LASSO regression with cross-validation.

        LASSO (L1 regularization) naturally performs feature selection by
        shrinking coefficients to zero.

        Args:
            X: Feature matrix
            y: Target variable
            verbose: Whether to log progress

        Returns:
            X_selected: DataFrame with selected features
        """
        # Scale features for LASSO
        X_scaled = self.scaler.fit_transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        # Fit LASSO with cross-validation
        lasso = LassoCV(
            cv=5,
            random_state=self.random_state,
            max_iter=10000,
            n_alphas=100,
            selection='random',  # Better for correlated features
            n_jobs=-1
        )

        try:
            lasso.fit(X_scaled_df, y)

            # Keep features with non-zero coefficients
            coef_mask = np.abs(lasso.coef_) > 1e-5
            selected_cols = X.columns[coef_mask].tolist()

            if verbose:
                logger.info(f"LASSO selected {len(selected_cols)} features with alpha={lasso.alpha_:.4f}")

            # If LASSO selected too few features, keep top by coefficient magnitude
            if len(selected_cols) < self.target_features:
                coef_abs = np.abs(lasso.coef_)
                top_indices = np.argsort(coef_abs)[-self.target_features:]
                selected_cols = X.columns[top_indices].tolist()
                if verbose:
                    logger.info(f"LASSO selected too few, keeping top {len(selected_cols)} by coefficient")

            return X[selected_cols] if selected_cols else X

        except Exception as e:
            logger.warning(f"LASSO selection failed: {e}. Returning all features.")
            return X

    def _rfe_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Recursive Feature Elimination using RandomForest.

        RFE recursively removes features and builds a model on the remaining
        features. It uses RandomForest to capture non-linear relationships.

        Args:
            X: Feature matrix
            y: Target variable
            verbose: Whether to log progress

        Returns:
            X_selected: DataFrame with target number of features
        """
        if len(X.columns) <= self.target_features:
            return X

        # Use RandomForest for RFE (captures non-linear relationships)
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=5,  # Shallow trees to prevent overfitting
            min_samples_split=10,
            random_state=self.random_state,
            n_jobs=-1
        )

        # Perform RFE
        rfe = RFE(
            estimator=rf,
            n_features_to_select=self.target_features,
            step=1  # Remove one feature at a time
        )

        try:
            rfe.fit(X, y)

            # Select features
            selected_cols = X.columns[rfe.support_].tolist()

            if verbose:
                logger.info(f"RFE selected {len(selected_cols)} features")

                # Show feature ranking
                ranking = pd.DataFrame({
                    'feature': X.columns,
                    'rank': rfe.ranking_
                }).sort_values('rank')
                logger.debug(f"Top 10 features by RFE ranking:\n{ranking.head(10)}")

            return X[selected_cols]

        except Exception as e:
            logger.warning(f"RFE selection failed: {e}. Returning input features.")
            return X

    def _calculate_feature_importance(self, X: pd.DataFrame, y: pd.Series):
        """
        Calculate feature importance scores for selected features.

        Uses RandomForest to estimate feature importance.

        Args:
            X: Selected features
            y: Target variable
        """
        try:
            # Train RandomForest for feature importance
            rf = RandomForestRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=self.random_state,
                n_jobs=-1
            )
            rf.fit(X, y)

            # Store feature importance
            self.feature_importance_ = pd.DataFrame({
                'feature': X.columns,
                'importance': rf.feature_importances_
            }).sort_values('importance', ascending=False)

        except Exception as e:
            logger.warning(f"Could not calculate feature importance: {e}")
            self.feature_importance_ = None

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance scores.

        Returns:
            DataFrame with feature names and importance scores, or None if not fitted
        """
        if not self._is_fitted:
            logger.warning("FeatureSelector not fitted. Call fit_select first.")
            return None

        return self.feature_importance_

    def save(self, filepath: str):
        """
        Save fitted selector to disk.

        Args:
            filepath: Path to save the selector
        """
        if not self._is_fitted:
            raise ValueError("Cannot save unfitted FeatureSelector")

        joblib.dump(self, filepath)
        logger.info(f"FeatureSelector saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'FeatureSelector':
        """
        Load fitted selector from disk.

        Args:
            filepath: Path to load from

        Returns:
            Loaded FeatureSelector instance
        """
        selector = joblib.load(filepath)
        if not isinstance(selector, cls):
            raise ValueError(f"Loaded object is not a FeatureSelector: {type(selector)}")

        logger.info(f"FeatureSelector loaded from {filepath}")
        return selector

    def __repr__(self) -> str:
        """String representation of the selector."""
        status = "fitted" if self._is_fitted else "not fitted"
        n_selected = len(self.selected_features) if self._is_fitted else 0
        return (
            f"FeatureSelector(target_features={self.target_features}, "
            f"correlation_threshold={self.correlation_threshold}, "
            f"status={status}, selected={n_selected})"
        )