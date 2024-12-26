"""Konfigurations-Flow für die Schulferien-Integration."""

from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN, COUNTRIES, REGIONS

_LOGGER = logging.getLogger(__name__)

class SchulferienFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurations-Flow für die Schulferien-Integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Schritt zur Auswahl von Land und Region."""
        errors = {}

        if user_input is not None:
            country_code = user_input["country"]
            region_name = user_input["region"]

            # Ermittelt den Regionscode basierend auf dem Namen
            region_code = next(
                (code for code, name in REGIONS[country_code].items() if name == region_name),
                None
            )

            if region_code:
                # Weiter zum nächsten Schritt
                return await self.async_step_finish(
                    user_input={"country": country_code, "region": region_code}
                )

            errors["region"] = "ungültige_region"

        # Formular zur Eingabe anzeigen
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("country"): vol.In(dict(COUNTRIES)),
                    vol.Required("region"): vol.In(list(REGIONS.get("DE", {}).values())),
                }
            ),
            errors=errors,
        )

    async def async_step_finish(self, user_input=None):
        """Prüft die Konfiguration und erstellt den Eintrag."""
        if user_input is None:
            return self.async_abort(reason="fehlende_eingabe")

        # Validierung der Eingabedaten
        if not user_input.get("country") or not user_input.get("region"):
            return self.async_abort(reason="fehlende_konfiguration")

        try:
            # Eintrag erstellen
            return self.async_create_entry(
                title="Schulferien-Integration",
                data=user_input,
                description=(
                    "Die Schulferien-Integration wurde erfolgreich eingerichtet.\n\n"
                    "Um Brückentage hinzuzufügen, bearbeiten Sie die Konfigurationsdatei unter:\n\n"
                    "`custom_components/schulferien/bridge_days.yaml`\n\n"
                    "Fügen Sie dort Ihre Brückentage im Format `DD.MM.YYYY` hinzu."
                ),
            )
        except (vol.Invalid, KeyError) as e:
            _LOGGER.error("Fehler beim Erstellen des Eintrags: %s", e)
            return self.async_abort(reason="erstellungsfehler")

    def is_matching(self, domain: str) -> bool:
        """Überprüft, ob die Domain übereinstimmt."""
        return domain == DOMAIN
