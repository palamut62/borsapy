"""
Portfoy Dengeleme (Portfolio Rebalancing)
=========================================

Hedef agirliklar belirleme, sapma analizi ve
otomatik dengeleme islemlerini gosterir.

borsapy'nin Portfolio sinifinin rebalancing ozelliklerini kullanir.

Kullanim:
    python examples/portfolio_rebalancing.py
"""

import borsapy as bp


def create_sample_portfolio() -> bp.Portfolio:
    """Ornek coklu varlik portfoyu olustur."""

    portfolio = bp.Portfolio()

    # Hisseler
    portfolio.add("THYAO", shares=100, cost=250.0)
    portfolio.add("GARAN", shares=300, cost=45.0)
    portfolio.add("ASELS", shares=50, cost=55.0)

    # Altin (FX)
    portfolio.add("gram-altin", shares=5, cost=2800.0, asset_type="fx")

    # Fon
    portfolio.add("YAY", shares=1000, cost=2.5, asset_type="fund")

    return portfolio


def show_drift_analysis(portfolio: bp.Portfolio, verbose: bool = True):
    """Sapma (drift) analizini goster."""

    drift_df = portfolio.drift()

    if verbose:
        print("\n--- SAPMA ANALIZI ---")
        print(f"{'Sembol':<15} {'Mevcut':>10} {'Hedef':>10} {'Sapma':>10} {'Sapma%':>8}")
        print("-" * 55)
        for _, row in drift_df.iterrows():
            print(
                f"{row['symbol']:<15} "
                f"{row['current_weight']:>10.2%} "
                f"{row['target_weight']:>10.2%} "
                f"{row['drift']:>+10.4f} "
                f"{row['drift_pct']:>+7.2f}%"
            )
        print()

    return drift_df


def show_rebalance_plan(portfolio: bp.Portfolio, threshold: float = 0.02, verbose: bool = True):
    """Dengeleme planini goster."""

    plan = portfolio.rebalance_plan(threshold=threshold)

    if verbose:
        print(f"\n--- DENGELEME PLANI (esik: {threshold:.0%}) ---")
        print(f"{'Sembol':<15} {'Mevcut':>10} {'Hedef':>10} {'Fark':>10} {'Deger(TL)':>12} {'Islem':>6}")
        print("-" * 65)
        for _, row in plan.iterrows():
            print(
                f"{row['symbol']:<15} "
                f"{row['current_shares']:>10.2f} "
                f"{row['target_shares']:>10.2f} "
                f"{row['delta_shares']:>+10.2f} "
                f"{row['delta_value']:>+12.2f} "
                f"{row['action']:>6}"
            )
        print()

    return plan


def run_rebalance(portfolio: bp.Portfolio, threshold: float = 0.02, verbose: bool = True):
    """Dengeleme islemini calistir ve oncesi/sonrasi karsilastir."""

    if verbose:
        print("\n=== DENGELEME ONCESI ===")
        print(f"Portfoy degeri: {portfolio.value:,.2f} TL")
        weights_before = portfolio.weights
        for symbol, weight in weights_before.items():
            print(f"  {symbol}: {weight:.2%}")

    # Dengelemeyi calistir
    plan = portfolio.rebalance(threshold=threshold)

    if verbose:
        print("\n=== DENGELEME SONRASI ===")
        print(f"Portfoy degeri: {portfolio.value:,.2f} TL")
        weights_after = portfolio.weights
        for symbol, weight in weights_after.items():
            print(f"  {symbol}: {weight:.2%}")

        # Hedef ile karsilastir
        print("\n--- HEDEF KARSILASTIRMA ---")
        targets = portfolio.target_weights
        for symbol in sorted(set(weights_after) | set(targets)):
            actual = weights_after.get(symbol, 0)
            target = targets.get(symbol, 0)
            diff = actual - target
            print(f"  {symbol}: {actual:.2%} (hedef: {target:.2%}, fark: {diff:+.2%})")

    return plan


def export_import_demo(portfolio: bp.Portfolio, verbose: bool = True):
    """Export/import ile hedef agirlik korunumu goster."""

    data = portfolio.to_dict()

    if verbose:
        print("\n--- EXPORT/IMPORT ---")
        print(f"Holdings: {len(data['holdings'])}")
        if "target_weights" in data:
            print(f"Hedef agirliklar: {data['target_weights']}")

    # Import
    portfolio2 = bp.Portfolio.from_dict(data)

    if verbose:
        print(f"Import sonrasi hedefler: {portfolio2.target_weights}")
        print(f"Hedefler korundu: {portfolio2.target_weights == portfolio.target_weights}")


def main():
    """Ana fonksiyon."""

    print("=" * 60)
    print("  PORTFOY DENGELEME ORNEGI")
    print("=" * 60)

    # 1. Portfoy olustur
    portfolio = create_sample_portfolio()
    print(f"\nPortfoy olusturuldu: {len(portfolio)} varlik")
    print(f"Toplam deger: {portfolio.value:,.2f} TL")

    # 2. Hedef agirliklar belirle
    portfolio.set_target_weights({
        "THYAO": 0.30,
        "GARAN": 0.20,
        "ASELS": 0.15,
        "gram-altin": 0.20,
        "YAY": 0.15,
    })
    print("\nHedef agirliklar belirlendi:")
    for symbol, weight in portfolio.target_weights.items():
        print(f"  {symbol}: {weight:.0%}")

    # 3. Sapma analizi
    show_drift_analysis(portfolio)

    # 4. Dengeleme plani
    show_rebalance_plan(portfolio, threshold=0.02)

    # 5. Dengeleme calistir
    run_rebalance(portfolio, threshold=0.02)

    # 6. Export/Import
    export_import_demo(portfolio)

    print("\n" + "=" * 60)
    print("  Tamamlandi!")
    print("=" * 60)


if __name__ == "__main__":
    main()
