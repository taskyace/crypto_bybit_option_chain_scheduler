import requests
import pandas as pd
from datetime import datetime
import sqlite3
import os

DB_PATH = "data/option_chains.db"

def get_option_chain(base_coin):
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "option", "baseCoin": base_coin}
    response = requests.get(url, params=params)
    if not response.ok or not response.text:
    print(f"⚠️ Errore: risposta vuota o non valida per {base_coin}")
    return pd.DataFrame()

    try:
        data = response.json()
    except Exception as e:
        print(f"⚠️ Errore nel parsing JSON per {base_coin}: {e}")
        print(f"Contenuto risposta: {response.text}")
        return pd.DataFrame()

    rows = []
    for opt in data.get("result", {}).get("list", []):
        symbol = opt.get('symbol', '')
        if base_coin not in symbol or symbol.count("-") != 4:
            continue

        try:
            _, expiry, strike, opt_type, coin = symbol.split("-")
            expiry_date = pd.to_datetime(expiry, format="%d%b%y", errors='coerce')
            if pd.isna(expiry_date):
                continue
            strike = float(strike)
            bid = float(opt['bid1Price']) if opt['bid1Price'] else None
            ask = float(opt['ask1Price']) if opt['ask1Price'] else None
            iv = float(opt['markIv']) if opt['markIv'] else None
            mid = round((bid + ask) / 2, 4) if bid is not None and ask is not None else None

            rows.append({
                "symbol": symbol,
                "scadenza": expiry_date.strftime("%Y-%m-%d"),
                "tipo": opt_type,
                "strike": strike,
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "IV": iv,
                "download_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            print(f"Errore parsing simbolo {symbol}: {e}")

    df = pd.DataFrame(rows)
    if df.empty:
        print(f"Nessuna opzione valida trovata per {base_coin}")
    return df.sort_values(by=["scadenza", "strike", "tipo"]).reset_index(drop=True)

def save_to_db(df, conn):
    # Crea tabella se non esiste
    conn.execute('''
    CREATE TABLE IF NOT EXISTS option_chain (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        scadenza TEXT,
        tipo TEXT,
        strike REAL,
        bid REAL,
        ask REAL,
        mid REAL,
        IV REAL,
        download_date TEXT
    )
    ''')

    # Inserisci dati con upsert per evitare duplicati (qui semplice insert)
    df.to_sql('option_chain', conn, if_exists='append', index=False)

def main():
    coins = ["BTC", "ETH", "SOL"]

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    for coin in coins:
        print(f"Scaricando option chain per {coin} ...")
        df = get_option_chain(coin)
        if not df.empty:
            save_to_db(df, conn)
            print(f"Dati per {coin} salvati su DB.")
        else:
            print(f"Nessun dato per {coin}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
