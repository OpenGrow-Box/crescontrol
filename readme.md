# CresControl - Home Assistant Integration 🌱

**CresControl** ist ein leistungsstarker Controller von [Cre.science](https://cre.science/crescontrol-grow-controller/), der speziell für die Steuerung von Umgebungsbedingungen in Grow-Räumen entwickelt wurde. Diese Integration ermöglicht die einfache Einbindung von CresControl in [Home Assistant](https://www.home-assistant.io/), um das Pflanzenwachstum präzise zu automatisieren und zu überwachen.

## Features 🌟

- **Einfache Integration in Home Assistant**: Steuerung und Automatisierung direkt über die Home Assistant Plattform.
- **Volle Kontrolle über die Grow-Box**: Reguliere Beleuchtung, Lüftung und Bewässerung über den CresControl.
- **Live-Monitoring**: Überwache wichtige Umgebungsparameter wie Temperatur, Luftfeuchtigkeit und CO2 in Echtzeit.
- **Zeit- und Eventbasierte Automatisierung**: Automatisiere den Betrieb Deiner Geräte nach Zeitplänen oder Umweltbedingungen.
- **Benachrichtigungen & Alarme**: Erhalte Benachrichtigungen, wenn Parameter außerhalb des optimalen Bereichs liegen.

## Voraussetzungen ⚙️

- Ein CresControl-Gerät von [Cre.science](https://cre.science/crescontrol-grow-controller/)
- Ein laufender **Home Assistant** Server

## Installation 🛠️

1. **Home Assistant vorbereiten**: Stelle sicher, dass Dein Home Assistant korrekt läuft und ein MQTT-Broker konfiguriert ist.
   
2. **CresControl einrichten**:
   - Folge der Anleitung auf [Cre.science](https://cre.science/crescontrol-grow-controller/), um CresControl in Betrieb zu nehmen.
   - Verbinde das CresControl über MQTT mit Deinem Home Assistant.

3. **Home Assistant Integration hinzufügen**:
   - Klone dieses Repository:
     ```bash
     git clone https://github.com/OpenGrow-Box/crescontrol.git
     ```
          cp -R crescontrol path/To/hmassitant/custom_components/.

4. **Geräte und Automatisierungen konfigurieren**: Nutze Home Assistant, um Automatisierungen basierend auf den Sensorwerten zu erstellen, z.B. das Ein- und Ausschalten von Ventilatoren oder Lampen.

