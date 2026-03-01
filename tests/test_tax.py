"""Tests for withholding tax (stopaj) rates feature."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from borsapy.fund import Fund
from borsapy.tax import (
    TAX_CAT_EQUITY_HEAVY,
    TAX_CAT_GSYF_GYF_LONG,
    TAX_CAT_GSYF_GYF_SHORT,
    TAX_CAT_OTHER,
    TAX_CAT_VARIABLE,
    classify_fund_tax_category,
    get_withholding_tax_rate,
    withholding_tax_rate,
    withholding_tax_table,
)

# =============================================================================
# Unit Tests: classify_fund_tax_category
# =============================================================================


class TestClassifyFundTaxCategory:
    """Tests for TEFAS category -> tax category mapping."""

    # --- FONKATEGORI values (from Fund.info "category") ---

    def test_degisken_fon(self):
        assert classify_fund_tax_category("Değişken Fon") == TAX_CAT_VARIABLE

    def test_serbest_fon(self):
        assert classify_fund_tax_category("Serbest Fon") == TAX_CAT_VARIABLE

    def test_karma_fon(self):
        assert classify_fund_tax_category("Karma Fon") == TAX_CAT_VARIABLE

    def test_fon_sepeti_fonu(self):
        assert classify_fund_tax_category("Fon Sepeti Fonu") == TAX_CAT_VARIABLE

    def test_borclanma_araclari_fonu(self):
        assert classify_fund_tax_category("Borçlanma Araçları Fonu") == TAX_CAT_OTHER

    def test_para_piyasasi_fonu(self):
        assert classify_fund_tax_category("Para Piyasası Fonu") == TAX_CAT_OTHER

    def test_kiymetli_madenler_fonu(self):
        assert classify_fund_tax_category("Kıymetli Madenler Fonu") == TAX_CAT_OTHER

    def test_katilim_fonu(self):
        assert classify_fund_tax_category("Katılım Fonu") == TAX_CAT_OTHER

    def test_girisim_sermayesi_yatirim_fonlari(self):
        assert classify_fund_tax_category("Girişim Sermayesi Yatırım Fonları") == TAX_CAT_GSYF_GYF_SHORT

    # --- FONTURACIKLAMA (Şemsiye) values (from management_fees) ---

    def test_degisken_semsiye(self):
        assert classify_fund_tax_category("Değişken Şemsiye Fonu") == TAX_CAT_VARIABLE

    def test_serbest_semsiye(self):
        assert classify_fund_tax_category("Serbest Şemsiye Fonu") == TAX_CAT_VARIABLE

    def test_borclanma_semsiye(self):
        assert classify_fund_tax_category("Borçlanma Araçları Şemsiye Fonu") == TAX_CAT_OTHER

    def test_katilim_semsiye(self):
        assert classify_fund_tax_category("Katılım Şemsiye Fonu") == TAX_CAT_OTHER

    def test_hisse_semsiye(self):
        assert classify_fund_tax_category("Hisse Senedi Şemsiye Fonu") == TAX_CAT_EQUITY_HEAVY

    # --- EMK-specific FONTURACIKLAMA values ---

    def test_emk_altin_fonu(self):
        assert classify_fund_tax_category("Altın Fonu") == TAX_CAT_OTHER

    def test_emk_dis_borclanma(self):
        assert classify_fund_tax_category("Dış Borçlanma Araçları Fonu") == TAX_CAT_VARIABLE

    def test_emk_standart_fon(self):
        assert classify_fund_tax_category("Standart Fon") == TAX_CAT_OTHER

    def test_emk_katilim_degisken(self):
        assert classify_fund_tax_category("Katılım Değişken Fon") == TAX_CAT_VARIABLE

    # --- Hisse Senedi Fonu with name disambiguation ---

    def test_hisse_fonu_domestic_default(self):
        """Domestic hisse senedi fonu defaults to equity heavy (0%)."""
        result = classify_fund_tax_category(
            "Hisse Senedi Fonu",
            "AK PORTFÖY BIST 30 HİSSE SENEDİ (TL) FONU (HİSSE SENEDİ YOĞUN FON)",
        )
        assert result == TAX_CAT_EQUITY_HEAVY

    def test_hisse_fonu_foreign_yabanci(self):
        """Foreign equity fund with 'YABANCI' in name → variable rate."""
        result = classify_fund_tax_category(
            "Hisse Senedi Fonu",
            "AK PORTFÖY AMERİKA YABANCI HİSSE SENEDİ FONU",
        )
        assert result == TAX_CAT_VARIABLE

    def test_hisse_fonu_plain_domestic(self):
        """Plain domestic hisse fonu without YOĞUN in name → still equity heavy."""
        result = classify_fund_tax_category(
            "Hisse Senedi Fonu",
            "INVEO PORTFÖY BİRİNCİ HİSSE SENEDİ FONU",
        )
        assert result == TAX_CAT_EQUITY_HEAVY

    # --- Legacy short-form values ---

    def test_legacy_degisken(self):
        assert classify_fund_tax_category("Değişken") == TAX_CAT_VARIABLE

    def test_legacy_eurobond(self):
        assert classify_fund_tax_category("Eurobond") == TAX_CAT_VARIABLE

    def test_legacy_borclanma_araclari(self):
        assert classify_fund_tax_category("Borçlanma Araçları") == TAX_CAT_OTHER

    def test_legacy_girisim_sermayesi(self):
        assert classify_fund_tax_category("Girişim Sermayesi") == TAX_CAT_GSYF_GYF_SHORT

    # --- Edge cases ---

    def test_unknown_returns_none(self):
        assert classify_fund_tax_category("BilinmeyenKategori") is None

    def test_empty_string_returns_none(self):
        assert classify_fund_tax_category("") is None

    def test_doviz_in_name_fallback(self):
        result = classify_fund_tax_category("BilinmeyenKategori", "XYZ Döviz Fonu")
        assert result == TAX_CAT_VARIABLE

    def test_doviz_fallback_case_insensitive(self):
        result = classify_fund_tax_category("Unknown", "ABC DÖVIZ SERBEST FON")
        assert result == TAX_CAT_VARIABLE

    def test_whitespace_stripped(self):
        assert classify_fund_tax_category("  Değişken Fon  ") == TAX_CAT_VARIABLE


# =============================================================================
# Unit Tests: get_withholding_tax_rate
# =============================================================================


class TestGetWithholdingTaxRate:
    """Tests for tax rate lookup by category and date."""

    # --- Variable (degisken/karma/doviz) ---

    def test_variable_before_2020(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2020, 1, 1))
        assert rate == 0.10

    def test_variable_period_2(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2023, 6, 15))
        assert rate == 0.10

    def test_variable_period_3(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2024, 7, 1))
        assert rate == 0.10

    def test_variable_period_4(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2024, 12, 1))
        assert rate == 0.10

    def test_variable_period_5(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2025, 6, 1))
        assert rate == 0.15

    def test_variable_period_6(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, date(2025, 8, 1))
        assert rate == 0.175

    # --- Equity heavy (pay senedi yogun) ---

    def test_equity_always_zero(self):
        for d in [date(2019, 1, 1), date(2023, 1, 1), date(2025, 12, 1)]:
            assert get_withholding_tax_rate(TAX_CAT_EQUITY_HEAVY, d) == 0.0

    # --- Other (borclanma/para/maden) ---

    def test_other_before_2020(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2020, 1, 1)) == 0.10

    def test_other_period_2_zero(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2021, 6, 1)) == 0.0

    def test_other_period_3(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2024, 8, 1)) == 0.075

    def test_other_period_4(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2024, 11, 15)) == 0.10

    def test_other_period_5(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2025, 3, 1)) == 0.15

    def test_other_period_6(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2025, 9, 1)) == 0.175

    # --- Boundary dates ---

    def test_boundary_period_1_end(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2020, 12, 22)) == 0.10

    def test_boundary_period_2_start(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2020, 12, 23)) == 0.0

    def test_boundary_period_2_end(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2024, 4, 30)) == 0.0

    def test_boundary_period_3_start(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2024, 5, 1)) == 0.075

    def test_boundary_period_5_end(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2025, 7, 8)) == 0.15

    def test_boundary_period_6_start(self):
        assert get_withholding_tax_rate(TAX_CAT_OTHER, date(2025, 7, 9)) == 0.175

    # --- GSYF/GYF holding duration ---

    def test_gsyf_short_holding(self):
        rate = get_withholding_tax_rate(TAX_CAT_GSYF_GYF_SHORT, date(2025, 6, 1), holding_days=300)
        assert rate == 0.15

    def test_gsyf_long_holding_override(self):
        rate = get_withholding_tax_rate(TAX_CAT_GSYF_GYF_SHORT, date(2025, 6, 1), holding_days=800)
        assert rate == 0.0

    def test_gsyf_exactly_730_days_is_short(self):
        rate = get_withholding_tax_rate(TAX_CAT_GSYF_GYF_SHORT, date(2025, 6, 1), holding_days=730)
        assert rate == 0.15

    def test_gsyf_731_days_is_long(self):
        rate = get_withholding_tax_rate(TAX_CAT_GSYF_GYF_SHORT, date(2025, 6, 1), holding_days=731)
        assert rate == 0.0

    def test_gsyf_long_category_always_zero(self):
        rate = get_withholding_tax_rate(TAX_CAT_GSYF_GYF_LONG, date(2025, 6, 1))
        assert rate == 0.0

    # --- String date parsing ---

    def test_string_date(self):
        rate = get_withholding_tax_rate(TAX_CAT_VARIABLE, "2025-06-01")
        assert rate == 0.15

    def test_string_date_iso_format(self):
        rate = get_withholding_tax_rate(TAX_CAT_OTHER, "2024-05-01")
        assert rate == 0.075

    # --- Error handling ---

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown tax category"):
            get_withholding_tax_rate("nonexistent", date(2025, 1, 1))

    def test_invalid_date_string_raises(self):
        with pytest.raises(ValueError):
            get_withholding_tax_rate(TAX_CAT_VARIABLE, "not-a-date")


# =============================================================================
# Unit Tests: withholding_tax_table
# =============================================================================


class TestWithholdingTaxTable:
    """Tests for the reference table output."""

    def test_returns_dataframe(self):
        df = withholding_tax_table()
        assert isinstance(df, pd.DataFrame)

    def test_correct_shape(self):
        df = withholding_tax_table()
        assert len(df) == 5
        # tax_category + description + 6 period columns = 8
        assert len(df.columns) == 8

    def test_has_required_columns(self):
        df = withholding_tax_table()
        assert "tax_category" in df.columns
        assert "description" in df.columns
        assert "<23.12.2020" in df.columns
        assert ">=09.07.2025" in df.columns

    def test_spot_check_values(self):
        df = withholding_tax_table()
        # Variable category, last period -> 17.5
        variable_row = df[df["tax_category"] == TAX_CAT_VARIABLE].iloc[0]
        assert variable_row[">=09.07.2025"] == 17.5
        assert variable_row["<23.12.2020"] == 10.0

    def test_equity_heavy_all_zero(self):
        df = withholding_tax_table()
        equity_row = df[df["tax_category"] == TAX_CAT_EQUITY_HEAVY].iloc[0]
        period_cols = [c for c in df.columns if c not in ("tax_category", "description")]
        for col in period_cols:
            assert equity_row[col] == 0.0

    def test_other_period_2_is_zero(self):
        df = withholding_tax_table()
        other_row = df[df["tax_category"] == TAX_CAT_OTHER].iloc[0]
        assert other_row["23.12.2020-30.04.2024"] == 0.0


# =============================================================================
# Unit Tests: Fund.tax_category and Fund.withholding_tax_rate (mocked)
# =============================================================================


def _make_fund_with_info(fund_code, info_dict):
    """Helper to create a Fund with mocked provider returning given info."""
    mock_provider = MagicMock()
    mock_provider.get_fund_detail.return_value = info_dict
    fund = Fund.__new__(Fund)
    fund._fund_code = fund_code
    fund._fund_type = "YAT"
    fund._provider = mock_provider
    fund._info_cache = None
    fund._detected_fund_type = None
    return fund


class TestFundTaxCategoryMocked:
    """Tests for Fund.tax_category property with mocked info."""

    def test_tax_category_borclanma(self):
        fund = _make_fund_with_info("AAK", {
            "category": "Kısa Vadeli Borçlanma",
            "name": "AK PORTFOY KISA VADELI BONO FON",
        })
        assert fund.tax_category == TAX_CAT_OTHER

    def test_tax_category_hisse_yogun(self):
        fund = _make_fund_with_info("HSF", {
            "category": "Hisse Senedi Yoğun",
            "name": "TEST HISSE FON",
        })
        assert fund.tax_category == TAX_CAT_EQUITY_HEAVY

    def test_tax_category_unknown_returns_none(self):
        fund = _make_fund_with_info("UNK", {
            "category": "UnknownCategory",
            "name": "TEST FON",
        })
        assert fund.tax_category is None

    def test_tax_category_doviz_name_fallback(self):
        fund = _make_fund_with_info("DVZ", {
            "category": "UnknownCategory",
            "name": "XYZ DÖVIZ SERBEST FON",
        })
        assert fund.tax_category == TAX_CAT_VARIABLE


class TestFundWithholdingTaxRateMocked:
    """Tests for Fund.withholding_tax_rate method with mocked info."""

    def test_rate_for_borclanma_period_5(self):
        fund = _make_fund_with_info("BRC", {
            "category": "Kısa Vadeli Borçlanma",
            "name": "TEST BORCLANMA FON",
        })
        rate = fund.withholding_tax_rate("2025-06-01")
        assert rate == 0.15

    def test_rate_for_equity_always_zero(self):
        fund = _make_fund_with_info("HSF", {
            "category": "Hisse Senedi Yoğun",
            "name": "TEST HISSE FON",
        })
        assert fund.withholding_tax_rate("2025-08-01") == 0.0

    def test_rate_unknown_category_returns_none(self):
        fund = _make_fund_with_info("UNK", {
            "category": "Unknown",
            "name": "TEST FON",
        })
        assert fund.withholding_tax_rate("2025-06-01") is None

    def test_rate_defaults_to_today(self):
        fund = _make_fund_with_info("DGS", {
            "category": "Değişken",
            "name": "TEST DEGISKEN FON",
        })
        rate = fund.withholding_tax_rate()
        assert isinstance(rate, float)
        assert rate >= 0.0


# =============================================================================
# Unit Tests: withholding_tax_rate convenience function (mocked)
# =============================================================================


class TestWithholdingTaxRateFunctionMocked:
    """Tests for the module-level withholding_tax_rate convenience function."""

    @patch("borsapy.fund.get_tefas_provider")
    def test_returns_rate(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_fund_detail.return_value = {
            "category": "Kısa Vadeli Borçlanma",
            "name": "TEST",
        }
        mock_get_provider.return_value = mock_provider

        rate = withholding_tax_rate("AAK", "2025-06-01")
        assert rate == 0.15

    @patch("borsapy.fund.get_tefas_provider")
    def test_unknown_category_returns_none(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_fund_detail.return_value = {
            "category": "Unknown",
            "name": "TEST",
        }
        mock_get_provider.return_value = mock_provider

        rate = withholding_tax_rate("UNK", "2025-06-01")
        assert rate is None

    @patch("borsapy.fund.get_tefas_provider")
    def test_defaults_to_today(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_fund_detail.return_value = {
            "category": "Değişken",
            "name": "TEST",
        }
        mock_get_provider.return_value = mock_provider

        rate = withholding_tax_rate("DGS")
        assert isinstance(rate, float)


# =============================================================================
# Integration Tests (require network)
# =============================================================================


@pytest.mark.integration
class TestTaxIntegration:
    """Integration tests requiring network connection."""

    def test_fund_tax_category_real(self):
        from borsapy.fund import Fund

        fund = Fund("AAK")
        cat = fund.tax_category
        # AAK is a short-term bond fund, should be classified
        assert cat is not None

    def test_fund_withholding_tax_rate_real(self):
        from borsapy.fund import Fund

        fund = Fund("AAK")
        rate = fund.withholding_tax_rate("2025-06-01")
        assert rate is not None
        assert 0.0 <= rate <= 0.5
