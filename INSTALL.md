# 🚀 Instalační návod - MPP Solar Home Assistant Integration

## 📋 Předpoklady

### Systémové požadavky
- ✅ **Home Assistant** 2023.1.0 nebo novější
- ✅ **Linux systém** (Raspberry Pi, Linux server)
- ✅ **MPP Solar měnič** série PIP (testováno na PIP5048MG)
- ✅ **USB připojení** mezi měničem a Home Assistant

### Ověření zařízení
```bash
# Zkontrolovat HID zařízení
ls -la /dev/hidraw*

# Mělo by zobrazit něco jako:
# crw-rw---- 1 root dialout 247, 2 Jan  1 12:00 /dev/hidraw2

# Ověřit USB připojení
lsusb | grep -i cypress
# Mělo by zobrazit: Bus 001 Device 003: ID 0665:5161 Cypress Semiconductor USB to Serial
```

## 🏠 Instalace přes HACS (Doporučeno)

### Krok 1: Přidání custom repository
1. Otevřete **HACS** v Home Assistant
2. Klikněte na **Integrations**
3. Klikněte na **⋮** (tři tečky) → **Custom repositories**
4. **URL:** `https://github.com/9991119990/mpp-solar-ha-integration`
5. **Kategorie:** `Integration`
6. Klikněte **Add**

### Krok 2: Instalace
1. Vyhledejte **"MPP Solar"** v HACS
2. Klikněte **Download**
3. **Restartujte Home Assistant**

## 🔧 Manuální instalace

### Krok 1: Stažení souborů
```bash
cd /config
wget https://github.com/9991119990/mpp-solar-ha-integration/archive/main.zip
unzip main.zip
```

### Krok 2: Kopírování souborů
```bash
mkdir -p /config/custom_components
cp -r mpp-solar-ha-integration-main/custom_components/mpp_solar /config/custom_components/
```

### Krok 3: Restart
Restartujte Home Assistant

## ⚙️ Konfigurace

### Krok 1: Nastavení oprávnění
```bash
# DŮLEŽITÉ: Spusťte před konfigurací!
sudo chmod 666 /dev/hidraw*

# Pro trvalé nastavení přidejte do /etc/udev/rules.d/99-hidraw.rules:
echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-hidraw.rules
sudo udevadm control --reload-rules
```

### Krok 2: Přidání integrace
1. **Settings** → **Devices & Services**
2. **Add Integration** → Vyhledejte **"MPP Solar"**
3. Vyplňte formulář:

| Pole | Hodnota | Popis |
|------|---------|-------|
| **Device Path** | `/dev/hidraw2` | Cesta k HID zařízení |
| **Protocol** | `PI30` | Komunikační protokol |
| **Name** | `MPP Solar Inverter` | Název zařízení |

### Krok 3: Ověření konfigurace
Po úspěšném přidání:
- ✅ Zařízení se zobrazí v **Devices & Services**
- ✅ Více než 50 entit bude dostupných
- ✅ Data se aktualizují každých 30 sekund

## 🔍 Řešení problémů

### ❌ "Cannot connect to device"
```bash
# 1. Zkontrolovat oprávnění
ls -la /dev/hidraw*
sudo chmod 666 /dev/hidraw*

# 2. Zkontrolovat USB připojení
lsusb | grep -i cypress
dmesg | tail -20

# 3. Zkontrolovat, že měnič běží
# Měnič musí být zapnutý a funkční
```

### ❌ "Device path does not exist"
```bash
# Najít správné HID zařízení
for device in /dev/hidraw*; do
    echo "Testing $device..."
    sudo python3 -c "
import time
try:
    with open('$device', 'rb+') as f:
        f.write(b'QID\x5e\x44\r')
        f.flush()
        time.sleep(0.1)
        response = f.read(100)
        if response:
            print('$device: Success - ', response)
        else:
            print('$device: No response')
except Exception as e:
    print('$device: Error - ', e)
"
done
```

### ❌ "Integration not found"
```bash
# Zkontrolovat správnou instalaci
ls -la /config/custom_components/mpp_solar/

# Mělo by obsahovat:
# __init__.py
# manifest.json
# config_flow.py
# sensor.py
# binary_sensor.py
# const.py
# mpp_solar_api.py
```

### ❌ "No data received"
```bash
# Test komunikace přímo s knihovnou
cd /home/dell/Měniče
source solar_env/bin/activate
python3 -c "
from mpp_solar_api import MPPSolarAPI
api = MPPSolarAPI('/dev/hidraw2', 'PI30')
print('Testing connection...')
result = api.test_connection()
print('Connection result:', result)
if result:
    data = api.get_all_data()
    print('Data received:', len(data), 'items')
"
```

## 🎯 Validace instalace

### Test 1: Kontrola entit
1. **Developer Tools** → **States**
2. Filtrovat podle `mpp_solar`
3. Mělo by zobrazit 50+ entit

### Test 2: Kontrola dat
```yaml
# V Developer Tools → Template
{{ states('sensor.mpp_solar_battery_capacity') }}
{{ states('sensor.mpp_solar_pv_input_power') }}
{{ states('binary_sensor.mpp_solar_is_load_on') }}
```

### Test 3: Kontrola logů
**Settings** → **System** → **Logs**
Filtrovat podle `mpp_solar` - neměly by být chyby

## 📊 Příklad Dashboard

```yaml
type: vertical-stack
cards:
  - type: entities
    title: "MPP Solar - Základní info"
    entities:
      - sensor.mpp_solar_device_mode
      - sensor.mpp_solar_battery_capacity
      - sensor.mpp_solar_pv_input_power
      - sensor.mpp_solar_ac_output_active_power
      - sensor.mpp_solar_inverter_heat_sink_temperature
  
  - type: history-graph
    title: "Výkon za posledních 24h"
    entities:
      - sensor.mpp_solar_pv_input_power
      - sensor.mpp_solar_ac_output_active_power
    hours_to_show: 24
```

## 🔄 Aktualizace

### HACS aktualizace
1. HACS → Integrations → MPP Solar
2. Kliknutí **Update**
3. Restart Home Assistant

### Manuální aktualizace
```bash
cd /config
rm -rf mpp-solar-ha-integration-main*
wget https://github.com/9991119990/mpp-solar-ha-integration/archive/main.zip
unzip main.zip
cp -r mpp-solar-ha-integration-main/custom_components/mpp_solar /config/custom_components/
# Restart Home Assistant
```

## 📞 Podpora

Pokud máte problémy:
1. **GitHub Issues:** https://github.com/9991119990/mpp-solar-ha-integration/issues
2. **Home Assistant komunita**
3. **Kontrola logů** v Home Assistant

---

**✅ Po dokončení instalace budete mít kompletní monitoring vašeho MPP Solar měniče v Home Assistant!**