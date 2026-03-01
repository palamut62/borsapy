"""
MetaStock Gostergeleri (HHV, LLV, MOM, ROC, WMA, DEMA, TEMA)
==============================================================

Klasik MetaStock teknik gostergelerini kullanarak
hisse analizi ve tarama ornekleri.

borsapy'nin teknik analiz fonksiyonlarini kullanir.

Kullanim:
    python examples/metastock_indicators.py
"""

import pandas as pd

import borsapy as bp


def analyze_hhv_llv(symbol: str, period: str = "1y", verbose: bool = True) -> dict:
    """HHV/LLV ile 52-hafta yuksek/dusuk analizi."""

    stock = bp.Ticker(symbol)
    df = stock.history(period=period)

    if df.empty:
        print(f"  {symbol}: Veri bulunamadi")
        return {}

    # 52-hafta (~252 islem gunu) HHV/LLV
    hhv_252 = bp.calculate_hhv(df, period=252, column="High")
    llv_252 = bp.calculate_llv(df, period=252, column="Low")

    # 20-gun HHV/LLV (kisa vadeli)
    hhv_20 = bp.calculate_hhv(df, period=20, column="High")
    llv_20 = bp.calculate_llv(df, period=20, column="Low")

    last_close = df["Close"].iloc[-1]
    high_52w = hhv_252.iloc[-1]
    low_52w = llv_252.iloc[-1]

    # Mevcut fiyatin 52-hafta araligindaki pozisyonu
    range_52w = high_52w - low_52w
    if range_52w > 0:
        position_pct = ((last_close - low_52w) / range_52w) * 100
    else:
        position_pct = 50.0

    result = {
        "symbol": symbol,
        "last_close": last_close,
        "hhv_252": high_52w,
        "llv_252": low_52w,
        "hhv_20": hhv_20.iloc[-1],
        "llv_20": llv_20.iloc[-1],
        "position_pct": position_pct,
        "distance_from_high": ((last_close - high_52w) / high_52w) * 100,
        "distance_from_low": ((last_close - low_52w) / low_52w) * 100,
    }

    if verbose:
        print(f"\n--- {symbol} HHV/LLV Analizi ---")
        print(f"  Son kapani: {last_close:.2f} TL")
        print(f"  52-Hafta Yuksek (HHV): {high_52w:.2f} TL")
        print(f"  52-Hafta Dusuk (LLV): {low_52w:.2f} TL")
        print(f"  20-Gun Yuksek: {hhv_20.iloc[-1]:.2f} TL")
        print(f"  20-Gun Dusuk: {llv_20.iloc[-1]:.2f} TL")
        print(f"  52H Araliktaki Pozisyon: %{position_pct:.1f}")
        print(f"  Yuksekten uzaklik: {result['distance_from_high']:+.1f}%")
        print(f"  Dusukten uzaklik: {result['distance_from_low']:+.1f}%")

    return result


def momentum_analysis(symbol: str, period: str = "1y", verbose: bool = True) -> dict:
    """MOM ve ROC ile momentum analizi."""

    stock = bp.Ticker(symbol)
    df = stock.history(period=period)

    if df.empty:
        print(f"  {symbol}: Veri bulunamadi")
        return {}

    # Farkli periyotlarda momentum
    mom_5 = bp.calculate_mom(df, period=5)
    mom_10 = bp.calculate_mom(df, period=10)
    mom_20 = bp.calculate_mom(df, period=20)

    # ROC (yuzdesel degisim)
    roc_5 = bp.calculate_roc(df, period=5)
    roc_10 = bp.calculate_roc(df, period=10)
    roc_20 = bp.calculate_roc(df, period=20)

    result = {
        "symbol": symbol,
        "mom_5": mom_5.iloc[-1],
        "mom_10": mom_10.iloc[-1],
        "mom_20": mom_20.iloc[-1],
        "roc_5": roc_5.iloc[-1],
        "roc_10": roc_10.iloc[-1],
        "roc_20": roc_20.iloc[-1],
    }

    if verbose:
        print(f"\n--- {symbol} Momentum Analizi ---")
        print(f"  MOM(5):  {mom_5.iloc[-1]:+.2f} TL  |  ROC(5):  {roc_5.iloc[-1]:+.2f}%")
        print(f"  MOM(10): {mom_10.iloc[-1]:+.2f} TL  |  ROC(10): {roc_10.iloc[-1]:+.2f}%")
        print(f"  MOM(20): {mom_20.iloc[-1]:+.2f} TL  |  ROC(20): {roc_20.iloc[-1]:+.2f}%")

        # Momentum yonu
        if mom_5.iloc[-1] > 0 and mom_10.iloc[-1] > 0 and mom_20.iloc[-1] > 0:
            print("  Yorum: Guclu yukselis momentumu")
        elif mom_5.iloc[-1] < 0 and mom_10.iloc[-1] < 0 and mom_20.iloc[-1] < 0:
            print("  Yorum: Guclu dusus momentumu")
        elif mom_5.iloc[-1] > 0 and mom_20.iloc[-1] < 0:
            print("  Yorum: Kisa vadeli toparlanma, uzun vade hala zayif")
        else:
            print("  Yorum: Karisik momentum sinyalleri")

    return result


def moving_average_comparison(symbol: str, period: str = "1y", verbose: bool = True) -> pd.DataFrame:
    """WMA, DEMA, TEMA'yi SMA ve EMA ile karsilastir."""

    stock = bp.Ticker(symbol)
    df = stock.history(period=period)

    if df.empty:
        print(f"  {symbol}: Veri bulunamadi")
        return pd.DataFrame()

    ma_period = 20
    last_close = df["Close"].iloc[-1]

    sma = bp.calculate_sma(df, period=ma_period)
    ema = bp.calculate_ema(df, period=ma_period)
    wma = bp.calculate_wma(df, period=ma_period)
    dema = bp.calculate_dema(df, period=ma_period)
    tema = bp.calculate_tema(df, period=ma_period)

    comparison = pd.DataFrame({
        "MA_Type": ["SMA", "EMA", "WMA", "DEMA", "TEMA"],
        "Period": [ma_period] * 5,
        "Value": [
            sma.iloc[-1], ema.iloc[-1], wma.iloc[-1],
            dema.iloc[-1], tema.iloc[-1]
        ],
        "vs_Close": [
            last_close - sma.iloc[-1],
            last_close - ema.iloc[-1],
            last_close - wma.iloc[-1],
            last_close - dema.iloc[-1],
            last_close - tema.iloc[-1],
        ],
    })

    comparison["Signal"] = comparison["vs_Close"].apply(
        lambda x: "YUKARI" if x > 0 else "ASAGI"
    )

    if verbose:
        print(f"\n--- {symbol} Hareketli Ortalama Karsilastirmasi (period={ma_period}) ---")
        print(f"  Son kapani: {last_close:.2f} TL\n")
        print(f"  {'Tip':<6} {'Deger':>10} {'Fark':>10} {'Sinyal':>8}")
        print(f"  {'-' * 36}")
        for _, row in comparison.iterrows():
            print(
                f"  {row['MA_Type']:<6} "
                f"{row['Value']:>10.2f} "
                f"{row['vs_Close']:>+10.2f} "
                f"{row['Signal']:>8}"
            )

        print("\n  Not: DEMA ve TEMA fiyat degisimlerine daha hizli tepki verir.")
        print("  WMA yakin gecmise daha fazla agirlik verir.")

    return comparison


def scan_with_metastock(symbols: list[str], verbose: bool = True) -> pd.DataFrame:
    """MetaStock kosullariyla hisse taramasi."""

    results = []

    for symbol in symbols:
        try:
            stock = bp.Ticker(symbol)
            df = stock.history(period="6mo")

            if df.empty or len(df) < 30:
                continue

            close = df["Close"].iloc[-1]
            hhv_20 = bp.calculate_hhv(df, period=20, column="High").iloc[-1]
            llv_20 = bp.calculate_llv(df, period=20, column="Low").iloc[-1]
            mom_10 = bp.calculate_mom(df, period=10).iloc[-1]
            roc_10 = bp.calculate_roc(df, period=10).iloc[-1]
            wma_20 = bp.calculate_wma(df, period=20).iloc[-1]

            # 20-gun range icinde pozisyon
            range_20 = hhv_20 - llv_20
            if range_20 > 0:
                pos_20 = ((close - llv_20) / range_20) * 100
            else:
                pos_20 = 50.0

            results.append({
                "symbol": symbol,
                "close": round(close, 2),
                "hhv_20": round(hhv_20, 2),
                "llv_20": round(llv_20, 2),
                "pos_20": round(pos_20, 1),
                "mom_10": round(mom_10, 2),
                "roc_10": round(roc_10, 2),
                "wma_20": round(wma_20, 2),
                "above_wma": close > wma_20,
            })
        except Exception as e:
            if verbose:
                print(f"  {symbol}: Hata - {e}")

    result_df = pd.DataFrame(results)

    if verbose and not result_df.empty:
        print(f"\n--- MetaStock Tarama Sonuclari ({len(results)} hisse) ---")

        # Guclu momentum (ROC > 5% ve WMA uzerinde)
        strong = result_df[(result_df["roc_10"] > 5) & result_df["above_wma"]]
        if not strong.empty:
            print(f"\n  Guclu Momentum (ROC>5%, WMA uzerinde): {len(strong)} hisse")
            for _, row in strong.iterrows():
                print(f"    {row['symbol']}: ROC={row['roc_10']:+.1f}%, Pos={row['pos_20']:.0f}%")

        # 20-gun dip yakininda (pozisyon < 20%)
        oversold = result_df[result_df["pos_20"] < 20]
        if not oversold.empty:
            print(f"\n  20-Gun Dip Yakininda (pos<20%): {len(oversold)} hisse")
            for _, row in oversold.iterrows():
                print(f"    {row['symbol']}: Pos={row['pos_20']:.0f}%, Close={row['close']:.2f}")

        # 20-gun tepe yakininda (pozisyon > 80%)
        overbought = result_df[result_df["pos_20"] > 80]
        if not overbought.empty:
            print(f"\n  20-Gun Tepe Yakininda (pos>80%): {len(overbought)} hisse")
            for _, row in overbought.iterrows():
                print(f"    {row['symbol']}: Pos={row['pos_20']:.0f}%, Close={row['close']:.2f}")

    return result_df


def main():
    """Ana fonksiyon."""

    print("=" * 60)
    print("  METASTOCK GOSTERGELERI ORNEGI")
    print("=" * 60)

    symbol = "THYAO"

    # 1. HHV/LLV Analizi
    analyze_hhv_llv(symbol)

    # 2. Momentum Analizi
    momentum_analysis(symbol)

    # 3. Hareketli Ortalama Karsilastirmasi
    moving_average_comparison(symbol)

    # 4. add_indicators ile toplu gosterge ekleme
    print("\n--- add_indicators() ile Toplu Gosterge ---")
    stock = bp.Ticker(symbol)
    df = stock.history(period="6mo")
    df_ind = bp.add_indicators(df, ["hhv", "llv", "mom", "roc", "wma", "dema", "tema"])
    print(f"  Eklenen sutunlar: {[c for c in df_ind.columns if c not in df.columns]}")
    print("  Son satir ornek degerleri:")
    for col in df_ind.columns:
        if col not in df.columns:
            print(f"    {col}: {df_ind[col].iloc[-1]:.2f}")

    # 5. MetaStock tarama (ornek semboller)
    print("\n--- XU030 Taramasi ---")
    try:
        xu030 = bp.Index("XU030")
        symbols = xu030.component_symbols[:10]  # Ilk 10 hisse
    except Exception:
        symbols = ["THYAO", "GARAN", "ASELS", "BIMAS", "AKBNK"]

    scan_with_metastock(symbols)

    # 6. CSV export
    print("\n--- CSV Export ---")
    if not df_ind.empty:
        csv_path = "metastock_output.csv"
        df_ind.to_csv(csv_path)
        print(f"  Veriler {csv_path} dosyasina kaydedildi")
        print(f"  {len(df_ind)} satir, {len(df_ind.columns)} sutun")

    print("\n" + "=" * 60)
    print("  Tamamlandi!")
    print("=" * 60)


if __name__ == "__main__":
    main()
