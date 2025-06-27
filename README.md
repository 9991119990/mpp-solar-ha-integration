# MPP Solar Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/9991119990/mpp-solar-ha-integration.svg)](https://github.com/9991119990/mpp-solar-ha-integration/releases)
[![License](https://img.shields.io/github/license/9991119990/mpp-solar-ha-integration.svg)](LICENSE)

Kompletní Home Assistant integrace pro MPP Solar invertory (měniče) řady PIP.

## 🌞 Podporované zařízení

- **MPP Solar PIP5048MG** (primárně testováno)
- **MPP Solar PIP série** (obecně kompatibilní)
- Protokol **PI30** přes USB HID rozhraní

## ✨ Funkce

### 📊 **Více než 50 senzorů:**
- **Napětí:** AC vstup/výstup, baterie, PV panely
- **Proudy:** Nabíjecí, vybíjecí, výstupní 
- **Výkony:** Činný, zdánlivý, PV výkon
- **Teplota:** Chladič měniče
- **Kapacita baterie** v %
- **Frekvence** AC
- **Zatížení** měniče v %

### 🚨 **Varování a alarmy:**
- 28 různých stavů chyb a varování
- Přehřátí, přetížení, napěťové chyby
- Stav ventilátoru, baterie, senzorů
- Binární senzory s příslušnými ikonami

### 🔧 **Stavové informace:**
- Režim práce (Battery/Line/Fault)
- Stav nabíjení (AC/Solar/Off)
- Zatížení a bypass stavy
- LCD a buzzer nastavení

## 🏠 Instalace

### Metoda 1: HACS (Doporučeno)

1. Otevřete HACS v Home Assistant
2. Přejděte na **Integrations**
3. Klikněte na **Custom repositories**
4. Přidejte URL: `https://github.com/9991119990/mpp-solar-ha-integration`
5. Kategorie: **Integration**
6. Klikněte **Install**
7. Restartujte Home Assistant

### Metoda 2: Manuální instalace

1. Stáhněte nejnovější release
2. Zkopírujte složku `custom_components/mpp_solar` do `<config>/custom_components/`
3. Restartujte Home Assistant

## ⚙️ Konfigurace

### Krok 1: Příprava zařízení

```bash
# Nastavit oprávnění pro HID zařízení
sudo chmod 666 /dev/hidraw*

# Ověřit, že zařízení existuje
ls -la /dev/hidraw*
```

### Krok 2: Přidání integrace

1. V Home Assistant přejděte na **Settings** → **Devices & Services**
2. Klikněte **Add Integration**
3. Vyhledejte **"MPP Solar"**
4. Zadejte parametry:
   - **Device Path:** `/dev/hidraw2` (nebo jiné dle vašeho systému)
   - **Protocol:** `PI30` (výchozí)
   - **Name:** `MPP Solar Inverter` (libovolné)

### Krok 3: Ověření

Po úspěšném přidání se zobrazí:
- Zařízení **"MPP Solar Inverter"** v seznamu
- Více než 50 entit (senzorů)
- Automatická aktualizace každých 30 sekund

## 📋 Dostupné entity

### 🔢 Senzory (sensor.*)
```
sensor.mpp_solar_ac_input_voltage
sensor.mpp_solar_ac_output_voltage  
sensor.mpp_solar_battery_voltage
sensor.mpp_solar_battery_capacity
sensor.mpp_solar_pv_input_voltage
sensor.mpp_solar_pv_input_power
sensor.mpp_solar_ac_output_active_power
sensor.mpp_solar_inverter_heat_sink_temperature
... a další
```

### 🔘 Binární senzory (binary_sensor.*)
```
binary_sensor.mpp_solar_is_load_on
binary_sensor.mpp_solar_is_charging_on
binary_sensor.mpp_solar_line_fail_warning
binary_sensor.mpp_solar_over_temperature_fault
binary_sensor.mpp_solar_battery_low_alarm_warning
... a další
```

## 🎨 Použití v Dashboard

### Příklad Energy Card
```yaml
type: energy
entities:
  - entity: sensor.mpp_solar_pv_input_power
    name: "Solar Production"
  - entity: sensor.mpp_solar_ac_output_active_power
    name: "Load Consumption"
  - entity: sensor.mpp_solar_battery_capacity
    name: "Battery Level"
```

### Příklad Gauge Card
```yaml
type: gauge
entity: sensor.mpp_solar_battery_capacity
min: 0
max: 100
severity:
  green: 50
  yellow: 20
  red: 0
```

## 🔧 Řešení problémů

### ❌ "Cannot connect to device"
```bash
# Zkontrolovat oprávnění
sudo chmod 666 /dev/hidraw*

# Ověřit existenci zařízení
ls -la /dev/hidraw*

# Zkontrolovat USB připojení
lsusb | grep -i cypress
```

### ❌ "Device path does not exist"
```bash
# Najít správné HID zařízení
sudo dmesg | grep -i "hidraw"
ls /dev/hidraw*

# V konfiguraci použít správnou cestu
```

### ❌ "No data received"
```bash
# Zkontrolovat, že měnič běží
# Zkontrolovat USB kabel
# Zkontrolovat, že žádná jiná aplikace nepoužívá zařízení
```

## 🚀 Rozšířené možnosti

### Automatizace při nízkém napětí baterie
```yaml
automation:
  - alias: "Low Battery Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.mpp_solar_battery_capacity
      below: 20
    action:
      service: notify.mobile_app
      data:
        message: "Baterie měniče je pod 20%!"
```

### Notifikace při chybách
```yaml
automation:
  - alias: "Inverter Fault Alert"
    trigger:
      platform: state
      entity_id: 
        - binary_sensor.mpp_solar_over_temperature_fault
        - binary_sensor.mpp_solar_overload_fault
      to: 'on'
    action:
      service: notify.mobile_app
      data:
        message: "Chyba měniče: {{ trigger.to_state.attributes.friendly_name }}"
```

## 📝 Technické detaily

- **Komunikace:** USB HID rozhraní
- **Protokol:** PI30
- **Aktualizace:** Každých 30 sekund
- **Timeout:** 5 sekund na příkaz
- **Podpora:** Home Assistant 2023.1+

## 🤝 Příspěvky

Vítáme příspěvky! Před vytvořením pull requestu prosím:

1. Forkněte repozitář
2. Vytvořte feature branch
3. Commitněte změny
4. Vytvořte pull request

## 📄 Licence

MIT License - viz [LICENSE](LICENSE) pro detaily.

## 🙏 Poděkování

- [mpp-solar](https://github.com/jblance/mpp-solar) - Inspirace a referenční implementace
- Home Assistant komunita
- Testovací uživatelé

## 📞 Podpora

- **Issues:** [GitHub Issues](https://github.com/9991119990/mpp-solar-ha-integration/issues)
- **Diskuse:** [GitHub Discussions](https://github.com/9991119990/mpp-solar-ha-integration/discussions)
- **Wiki:** [GitHub Wiki](https://github.com/9991119990/mpp-solar-ha-integration/wiki)

---

**Vytvořeno s ❤️ pro Home Assistant komunitu**