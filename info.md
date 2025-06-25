# MPP Solar Home Assistant Integration

Kompletní integrace pro MPP Solar invertory (měniče) řady PIP.

## Co tato integrace přidá

### 📊 Senzory
- **50+ senzorů** pro sledování všech parametrů měniče
- Napětí, proudy, výkony, teplota
- Kapacita baterie, frekvence AC
- PV výkon a napětí

### 🔴 Binární senzory  
- **28 stavových senzorů** pro varování a chyby
- Přehřátí, přetížení, napěťové problémy
- Stav nabíjení, zatížení, ventilátoru

### 🏠 Automatická detekce
- Plug & Play setup přes config flow
- Automatické rozpoznání zařízení
- Konfigurace přes UI

## Požadavky

- MPP Solar měnič řady PIP (testováno na PIP5048MG)
- USB připojení k Home Assistant
- Linux systém s přístupem k /dev/hidraw*

## Rychlá instalace

1. Nainstalujte přes HACS
2. Restartujte Home Assistant  
3. Přidejte integraci přes Settings → Integrations
4. Zadejte cestu k zařízení (např. /dev/hidraw2)

## Nastavení oprávnění

Před použitím spusťte:
```bash
sudo chmod 666 /dev/hidraw*
```

Po instalaci budete mít přístup ke všem datům z vašeho MPP Solar měniče přímo v Home Assistant!