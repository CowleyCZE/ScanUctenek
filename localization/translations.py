# Translation dictionary for SkenÚčtenek app

# Supported languages
LANGUAGES = ['cs', 'fr', 'de']
LANGUAGE_NAMES = {
    'cs': 'Čeština',
    'fr': 'Français',
    'de': 'Deutsch'
}

# Translations dictionary
TRANSLATIONS = {
    # App basics
    'app_name': {
        'cs': 'SkenÚčtenek',
        'fr': 'SkenÚčtenek',
        'de': 'SkenÚčtenek'
    },
    'app_description': {
        'cs': 'SkenÚčtenek je aplikace pro skenování účtenek, která automaticky extrahuje informace a exportuje je do Excelu.',
        'fr': 'SkenÚčtenek est une application de numérisation de reçus qui extrait automatiquement les informations et les exporte vers Excel.',
        'de': 'SkenÚčtenek ist eine Anwendung zum Scannen von Belegen, die automatisch Informationen extrahiert und nach Excel exportiert.'
    },
    
    # Navigation and tabs
    'scan_tab': {
        'cs': 'Skenovat',
        'fr': 'Scanner',
        'de': 'Scannen'
    },
    'history_tab': {
        'cs': 'Historie',
        'fr': 'Historique',
        'de': 'Verlauf'
    },
    'export_tab': {
        'cs': 'Export',
        'fr': 'Exporter',
        'de': 'Exportieren'
    },
    'settings_tab': {
        'cs': 'Nastavení',
        'fr': 'Paramètres',
        'de': 'Einstellungen'
    },
    
    # Scan page
    'scan_receipt': {
        'cs': 'Skenování účtenky',
        'fr': 'Scanner un reçu',
        'de': 'Beleg scannen'
    },
    'take_photo': {
        'cs': 'Vyfotit účtenku',
        'fr': 'Prendre une photo',
        'de': 'Foto aufnehmen'
    },
    'upload_receipt': {
        'cs': 'Nahrát soubor',
        'fr': 'Télécharger un fichier',
        'de': 'Datei hochladen'
    },
    'processing_receipt': {
        'cs': 'Zpracování účtenky...',
        'fr': 'Traitement du reçu...',
        'de': 'Beleg wird verarbeitet...'
    },
    'extracted_info': {
        'cs': 'Extrahované informace',
        'fr': 'Informations extraites',
        'de': 'Extrahierte Informationen'
    },
    'show_ocr_text': {
        'cs': 'Zobrazit rozpoznaný text',
        'fr': 'Afficher le texte reconnu',
        'de': 'Erkannten Text anzeigen'
    },
    'save_receipt': {
        'cs': 'Uložit účtenku',
        'fr': 'Enregistrer le reçu',
        'de': 'Beleg speichern'
    },
    'receipt_saved': {
        'cs': 'Účtenka byla úspěšně uložena!',
        'fr': 'Le reçu a été enregistré avec succès!',
        'de': 'Beleg wurde erfolgreich gespeichert!'
    },
    
    # Receipt fields
    'merchant': {
        'cs': 'Obchodník',
        'fr': 'Commerçant',
        'de': 'Händler'
    },
    'date': {
        'cs': 'Datum',
        'fr': 'Date',
        'de': 'Datum'
    },
    'total': {
        'cs': 'Celková částka',
        'fr': 'Montant total',
        'de': 'Gesamtbetrag'
    },
    'payment_method': {
        'cs': 'Způsob platby',
        'fr': 'Moyen de paiement',
        'de': 'Zahlungsart'
    },
    'receipt_number': {
        'cs': 'Číslo účtenky',
        'fr': 'Numéro du reçu',
        'de': 'Belegnummer'
    },
    'cash': {
        'cs': 'Hotovost',
        'fr': 'Espèces',
        'de': 'Bargeld'
    },
    'card': {
        'cs': 'Kartou',
        'fr': 'Carte',
        'de': 'Karte'
    },
    'other': {
        'cs': 'Jiné',
        'fr': 'Autre',
        'de': 'Andere'
    },
    
    # History page
    'receipt_history': {
        'cs': 'Historie účtenek',
        'fr': 'Historique des reçus',
        'de': 'Belegverlauf'
    },
    'no_receipts': {
        'cs': 'Zatím nemáte žádné uložené účtenky.',
        'fr': 'Vous n\'avez pas encore de reçus enregistrés.',
        'de': 'Sie haben noch keine gespeicherten Belege.'
    },
    'delete': {
        'cs': 'Smazat',
        'fr': 'Supprimer',
        'de': 'Löschen'
    },
    'receipt_deleted': {
        'cs': 'Účtenka byla smazána.',
        'fr': 'Le reçu a été supprimé.',
        'de': 'Der Beleg wurde gelöscht.'
    },
    
    # Export page
    'export_to_excel': {
        'cs': 'Export do Excelu',
        'fr': 'Exporter vers Excel',
        'de': 'Nach Excel exportieren'
    },
    'no_receipts_to_export': {
        'cs': 'Nemáte žádné účtenky k exportu.',
        'fr': 'Vous n\'avez pas de reçus à exporter.',
        'de': 'Sie haben keine Belege zum Exportieren.'
    },
    'excel_filename': {
        'cs': 'Název souboru Excel',
        'fr': 'Nom du fichier Excel',
        'de': 'Name der Excel-Datei'
    },
    'column_mapping': {
        'cs': 'Mapování sloupců',
        'fr': 'Mappage des colonnes',
        'de': 'Spaltenzuordnung'
    },
    'date_column': {
        'cs': 'Sloupec pro datum',
        'fr': 'Colonne pour la date',
        'de': 'Spalte für Datum'
    },
    'total_column': {
        'cs': 'Sloupec pro částku',
        'fr': 'Colonne pour le montant',
        'de': 'Spalte für Betrag'
    },
    'payment_method_column': {
        'cs': 'Sloupec pro způsob platby',
        'fr': 'Colonne pour le moyen de paiement',
        'de': 'Spalte für Zahlungsart'
    },
    'merchant_column': {
        'cs': 'Sloupec pro obchodníka',
        'fr': 'Colonne pour le commerçant',
        'de': 'Spalte für Händler'
    },
    'receipt_number_column': {
        'cs': 'Sloupec pro číslo účtenky',
        'fr': 'Colonne pour le numéro du reçu',
        'de': 'Spalte für Belegnummer'
    },
    'export': {
        'cs': 'Exportovat',
        'fr': 'Exporter',
        'de': 'Exportieren'
    },
    'exporting': {
        'cs': 'Exportuji...',
        'fr': 'Exportation en cours...',
        'de': 'Exportieren...'
    },
    'export_success': {
        'cs': 'Export byl úspěšný. Klikněte na tlačítko níže pro stažení.',
        'fr': 'Exportation réussie. Cliquez sur le bouton ci-dessous pour télécharger.',
        'de': 'Export erfolgreich. Klicken Sie auf die Schaltfläche unten, um herunterzuladen.'
    },
    'download_excel': {
        'cs': 'Stáhnout Excel soubor',
        'fr': 'Télécharger le fichier Excel',
        'de': 'Excel-Datei herunterladen'
    },
    
    # Settings page
    'settings': {
        'cs': 'Nastavení',
        'fr': 'Paramètres',
        'de': 'Einstellungen'
    },
    'about_app': {
        'cs': 'O aplikaci',
        'fr': 'À propos de l\'application',
        'de': 'Über die App'
    },
    'select_language': {
        'cs': 'Vyberte jazyk',
        'fr': 'Sélectionnez la langue',
        'de': 'Sprache auswählen'
    },
    'reset_data': {
        'cs': 'Resetovat data',
        'fr': 'Réinitialiser les données',
        'de': 'Daten zurücksetzen'
    },
    'clear_all_receipts': {
        'cs': 'Smazat všechny účtenky',
        'fr': 'Supprimer tous les reçus',
        'de': 'Alle Belege löschen'
    },
    'confirm_delete': {
        'cs': 'Opravdu chcete smazat všechny účtenky? Tato akce je nevratná.',
        'fr': 'Voulez-vous vraiment supprimer tous les reçus? Cette action est irréversible.',
        'de': 'Möchten Sie wirklich alle Belege löschen? Dieser Vorgang kann nicht rückgängig gemacht werden.'
    },
    'all_receipts_deleted': {
        'cs': 'Všechny účtenky byly úspěšně smazány.',
        'fr': 'Tous les reçus ont été supprimés avec succès.',
        'de': 'Alle Belege wurden erfolgreich gelöscht.'
    },
    'no_receipts_to_delete': {
        'cs': 'Nemáte žádné účtenky ke smazání.',
        'fr': 'Vous n\'avez pas de reçus à supprimer.',
        'de': 'Sie haben keine Belege zum Löschen.'
    }
}

def get_text(key, language='cs'):
    """
    Get translated text for a given key and language
    
    Args:
        key: Translation key
        language: Language code ('cs', 'fr', 'de')
    
    Returns:
        Translated text string
    """
    # Default to Czech if language not supported
    if language not in LANGUAGES:
        language = 'cs'
    
    # Get translation or return the key if not found
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(language, TRANSLATIONS[key].get('cs', key))
    else:
        return key
