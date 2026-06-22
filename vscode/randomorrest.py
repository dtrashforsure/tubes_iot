import time
import requests
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# =========================================================
# KONFIGURASI THINGSPEAK
# =========================================================
CHANNEL_ID = "3413573"

# Channel public, jadi Read API Key tidak dipakai
READ_API_KEY = ""

# Write API Key untuk mengirim hasil AI ke ThingSpeak
WRITE_API_KEY = "ISI_WRITE_API_KEY_ANDA"  # ganti dengan API key ThingSpeak Anda

READ_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
WRITE_URL = "https://api.thingspeak.com/update"


# =========================================================
# PARAMETER SISTEM
# =========================================================
# Wokwi mengirim data setiap 15 detik (batas aman ThingSpeak)
DATA_INTERVAL_SECOND = 15

# Prediksi dibuat 1 menit ke depan
PREDICTION_HORIZON_SECOND = 60

# 1 menit / 15 detik = 4 data ke depan
PREDICTION_STEPS = int(PREDICTION_HORIZON_SECOND / DATA_INTERVAL_SECOND)

# Python membaca data setiap 10 detik
AI_READ_INTERVAL_SECOND = 10

# Python menulis prediksi setiap 45 detik (hindari rate limit ThingSpeak)
AI_WRITE_INTERVAL_SECOND = 45

# Minimal data fitur untuk training
MIN_FEATURE_DATA = 5


# =========================================================
# KLASIFIKASI SUHU
# 0 = Dingin
# 1 = Normal
# 2 = Panas
# =========================================================
def classify_temperature(temp: float) -> int:
    if temp < 25.0:
        return 0
    elif 25.0 <= temp <= 30.0:
        return 1
    else:
        return 2


def label_text(label: int) -> str:
    if label == 0:
        return "DINGIN"
    elif label == 1:
        return "NORMAL"
    elif label == 2:
        return "PANAS"
    else:
        return "TIDAK DIKETAHUI"


# =========================================================
# MEMBACA DATA SUHU DARI THINGSPEAK PUBLIC CHANNEL
# =========================================================
def read_temperature_data(results: int = 200):
    params = {
        "results": results
    }

    try:
        response = requests.get(READ_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as error:
        print("Gagal koneksi ke ThingSpeak")
        print("Error:", error)
        return None

    if response.status_code != 200 or response.text.strip() == "-1":
        print("Gagal membaca data dari ThingSpeak")
        print("HTTP Status:", response.status_code)
        print("Response:", response.text)
        print("Cek Channel ID atau status Public channel.")
        return None

    try:
        data = response.json()
    except ValueError:
        print("Response ThingSpeak bukan JSON.")
        print("Response:", response.text)
        return None

    feeds = data.get("feeds", [])

    rows = []

    for feed in feeds:
        entry_id = feed.get("entry_id")
        created_at = feed.get("created_at")
        temp_value = feed.get("field1")

        if temp_value is not None:
            try:
                rows.append({
                    "entry_id": entry_id,
                    "created_at": created_at,
                    "temperature": float(temp_value)
                })
            except ValueError:
                pass

    if len(rows) == 0:
        print("Belum ada data suhu valid pada Field 1 ThingSpeak")
        return None

    df = pd.DataFrame(rows)
    df = df.dropna()
    df = df.reset_index(drop=True)

    return df


# =========================================================
# MEMBUAT FITUR TIME SERIES
# =========================================================
def create_time_series_features(df: pd.DataFrame):
    df = df.copy()

    df["temp_lag_1"] = df["temperature"].shift(1)
    df["temp_lag_2"] = df["temperature"].shift(2)
    df["temp_lag_3"] = df["temperature"].shift(3)

    df["temp_change"] = df["temperature"] - df["temp_lag_1"]

    df["moving_avg_3"] = df["temperature"].rolling(window=3).mean()
    df["moving_avg_5"] = df["temperature"].rolling(window=5).mean()

    # Target prediksi: suhu 1 menit ke depan
    df["target_future"] = df["temperature"].shift(-PREDICTION_STEPS)

    df = df.dropna()
    df = df.reset_index(drop=True)

    return df


# =========================================================
# TRAINING RANDOM FOREST REGRESSOR
# =========================================================
def train_random_forest_regressor(df_feature: pd.DataFrame):
    feature_columns = [
        "temperature",
        "temp_lag_1",
        "temp_lag_2",
        "temp_lag_3",
        "temp_change",
        "moving_avg_3",
        "moving_avg_5"
    ]

    X = df_feature[feature_columns]
    y = df_feature["target_future"]

    if len(df_feature) < MIN_FEATURE_DATA:
        print("Data belum cukup untuk training Random Forest.")
        print(f"Minimal data fitur: {MIN_FEATURE_DATA}")
        return None

    split_index = int(len(df_feature) * 0.8)

    # Kalau data terlalu sedikit, pakai semua data untuk training
    if split_index < 2:
        X_train = X
        y_train = y
        X_test = X
        y_test = y
    else:
        X_train = X.iloc[:split_index]
        X_test = X.iloc[split_index:]
        y_train = y.iloc[:split_index]
        y_test = y.iloc[split_index:]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        max_depth=6
    )

    model.fit(X_train, y_train)

    if len(X_test) > 0:
        y_pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        if len(y_test) > 1:
            r2 = r2_score(y_test, y_pred)
        else:
            r2 = 0.0

        print("======================================")
        print("EVALUASI MODEL RANDOM FOREST REGRESSOR")
        print("======================================")
        print(f"Jumlah data fitur : {len(df_feature)}")
        print(f"Jumlah training   : {len(X_train)}")
        print(f"Jumlah testing    : {len(X_test)}")
        print(f"MAE               : {mae:.3f} °C")
        print(f"RMSE              : {rmse:.3f} °C")
        print(f"R2 Score          : {r2:.3f}")
        print("======================================")

    return model


# =========================================================
# MEMBUAT INPUT TERBARU UNTUK PREDIKSI
# =========================================================
def create_latest_input(df: pd.DataFrame):
    if len(df) < 5:
        print("Data belum cukup untuk membuat input prediksi.")
        print("Minimal butuh 5 data suhu.")
        return None

    latest_temp = df["temperature"].iloc[-1]
    temp_lag_1 = df["temperature"].iloc[-2]
    temp_lag_2 = df["temperature"].iloc[-3]
    temp_lag_3 = df["temperature"].iloc[-4]

    temp_change = latest_temp - temp_lag_1
    moving_avg_3 = df["temperature"].iloc[-3:].mean()
    moving_avg_5 = df["temperature"].iloc[-5:].mean()

    input_data = pd.DataFrame([{
        "temperature": latest_temp,
        "temp_lag_1": temp_lag_1,
        "temp_lag_2": temp_lag_2,
        "temp_lag_3": temp_lag_3,
        "temp_change": temp_change,
        "moving_avg_3": moving_avg_3,
        "moving_avg_5": moving_avg_5
    }])

    return input_data


# =========================================================
# MENGIRIM HASIL AI KE THINGSPEAK
# Field 2 = prediksi suhu 1 menit ke depan
# Field 3 = status AI hasil prediksi
# =========================================================
def send_prediction_to_thingspeak(predicted_temp: float, predicted_status: int):
    params = {
        "api_key": WRITE_API_KEY,
        "field2": round(predicted_temp, 2),
        "field3": predicted_status
    }

    try:
        response = requests.get(WRITE_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as error:
        print("Gagal koneksi saat mengirim ke ThingSpeak")
        print("Error:", error)
        return False

    if response.status_code == 200 and response.text.strip() != "0":
        print("Prediksi AI berhasil dikirim ke ThingSpeak")
        print("Entry ID:", response.text)
        return True
    else:
        print("Gagal mengirim hasil AI ke ThingSpeak")
        print("HTTP Status:", response.status_code)
        print("Response:", response.text)
        print("Catatan: jika response = 0, kemungkinan update terlalu cepat.")
        return False


# =========================================================
# PROGRAM UTAMA
# =========================================================
def main():
    print("Program AI Random Forest - Prediksi Suhu 1 Menit ke Depan")
    print("Tekan CTRL + C untuk menghentikan program.")
    print()

    print(f"Channel ID              : {CHANNEL_ID}")
    print(f"Interval data sensor    : {DATA_INTERVAL_SECOND} detik")
    print(f"Horizon prediksi        : {PREDICTION_HORIZON_SECOND} detik")
    print(f"Jumlah step prediksi    : {PREDICTION_STEPS} data ke depan")
    print(f"Interval baca AI        : {AI_READ_INTERVAL_SECOND} detik")
    print(f"Interval tulis AI       : {AI_WRITE_INTERVAL_SECOND} detik")
    print()

    last_ai_write_time = 0

    while True:
        df = read_temperature_data(results=200)

        if df is not None:
            print("======================================")
            print(f"Jumlah data ThingSpeak terbaca : {len(df)}")
            print(f"Entry terakhir                 : {df['entry_id'].iloc[-1]}")
            print(f"Suhu terakhir                  : {df['temperature'].iloc[-1]:.2f} °C")
            print("======================================")

            df_feature = create_time_series_features(df)

            if len(df_feature) < MIN_FEATURE_DATA:
                print("Data historis belum cukup untuk prediksi.")
                print(f"Data fitur tersedia : {len(df_feature)}")
                print(f"Minimal data fitur  : {MIN_FEATURE_DATA}")

                estimated_min_raw = PREDICTION_STEPS + 5 + MIN_FEATURE_DATA
                print(f"Perkiraan minimal data mentah: {estimated_min_raw} entry")
                print("Biarkan Wokwi mengirim data beberapa menit lagi.")
                print()

                time.sleep(AI_READ_INTERVAL_SECOND)
                continue

            model = train_random_forest_regressor(df_feature)

            if model is not None:
                latest_input = create_latest_input(df)

                if latest_input is not None:
                    current_temp = df["temperature"].iloc[-1]

                    predicted_temp = model.predict(latest_input)[0]
                    predicted_status = classify_temperature(predicted_temp)
                    predicted_status_text = label_text(predicted_status)

                    print("======================================")
                    print("HASIL PREDIKSI AI")
                    print("======================================")
                    print(f"Suhu aktual sekarang       : {current_temp:.2f} °C")
                    print(f"Prediksi suhu 1 menit      : {predicted_temp:.2f} °C")
                    print(f"Status prediksi AI         : {predicted_status_text}")
                    print(f"AI Status Code             : {predicted_status}")
                    print("======================================")

                    current_time = time.time()

                    if current_time - last_ai_write_time >= AI_WRITE_INTERVAL_SECOND:
                        success = send_prediction_to_thingspeak(
                            predicted_temp=predicted_temp,
                            predicted_status=int(predicted_status)
                        )

                        if success:
                            last_ai_write_time = current_time
                    else:
                        remaining = AI_WRITE_INTERVAL_SECOND - (current_time - last_ai_write_time)
                        print(f"Menunggu {remaining:.0f} detik sebelum kirim AI berikutnya.")
                        print()

        time.sleep(AI_READ_INTERVAL_SECOND)


if __name__ == "__main__":
    main()
