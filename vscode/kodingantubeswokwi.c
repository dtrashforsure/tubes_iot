#include <WiFi.h>
#include <ThingSpeak.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ==========================
// WiFi Wokwi
// ==========================
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// ==========================
// ThingSpeak
// ==========================
WiFiClient client;

unsigned long channelID = 3413573;
const char* writeAPIKey = "ISI_WRITE_API_KEY_ANDA";

// ==========================
// DS18B20
// ==========================
#define ONE_WIRE_BUS 4

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ==========================
// Interval kirim data
// 15 detik = batas aman tercepat ThingSpeak
// ==========================
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 15000;

// ==========================
// Koneksi WiFi
// ==========================
void connectWiFi() {
  Serial.print("Menghubungkan ke WiFi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi terhubung");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// ==========================
// Cek koneksi WiFi
// ==========================
void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi terputus. Menghubungkan ulang...");

    WiFi.disconnect();
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }

    Serial.println();
    Serial.println("WiFi tersambung kembali");
  }
}

// ==========================
// Setup
// ==========================
void setup() {
  Serial.begin(115200);

  sensors.begin();

  connectWiFi();
  ThingSpeak.begin(client);

  // Supaya data langsung dikirim saat loop pertama
  lastSendTime = millis() - sendInterval;

  Serial.println("Sistem Monitoring Suhu DS18B20 Berbasis IoT Cerdas Dimulai");
  Serial.println("Interval pengiriman data ke ThingSpeak: 15 detik");
}

// ==========================
// Loop
// ==========================
void loop() {
  checkWiFiConnection();

  sensors.requestTemperatures();

  float temperature = sensors.getTempCByIndex(0);

  if (temperature == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor DS18B20 tidak terbaca. Cek wiring.");
    delay(2000);
    return;
  }

  Serial.println("================================");
  Serial.print("Suhu aktual : ");
  Serial.print(temperature);
  Serial.println(" °C");

  if (millis() - lastSendTime >= sendInterval) {
    // ESP32 hanya mengirim suhu aktual ke Field 1
    ThingSpeak.setField(1, temperature);

    int responseCode = ThingSpeak.writeFields(channelID, writeAPIKey);

    Serial.print("ThingSpeak response: ");
    Serial.println(responseCode);

    if (responseCode == 200) {
      Serial.println("Data suhu berhasil dikirim ke ThingSpeak Field 1");
    } else {
      Serial.println("Data suhu gagal dikirim ke ThingSpeak");
      Serial.println("Kemungkinan update terlalu cepat atau API Key salah.");
    }

    lastSendTime = millis();
  }

  delay(1000);
}
