# Hlasový Asistent pro Android

Tento projekt je open-source hlasový asistent pro Android. Je postaven na platformě **NativeScript** s použitím **TypeScriptu** a **Tailwind CSS**. Umožňuje uživatelům definovat vlastní hlasové příkazy a mapovat je na konkrétní akce, jako je volání webhooků nebo spouštění úloh v aplikaci Tasker.

## Klíčové funkce

- **Vlastní aktivační fráze:** Nastavte si vlastní "wake word" pro aktivaci asistenta.
- **Správa akcí:** Vytvářejte a spravujte neomezený počet vlastních hlasových příkazů.
- **Podpora Webhooků:** Spouštějte automatizaci v chytré domácnosti (Home Assistant, IFTTT, atd.) voláním libovolné URL adresy.
- **Integrace s Taskerem:** Ovládejte jakoukoliv funkci telefonu spouštěním úloh v populární automatizační aplikaci **Tasker**.
- **Zvuková zpětná vazba:** Volitelné zvukové signály pro lepší interakci.
- **Jednoduché rozhraní:** Přehledné a snadno ovladatelné rozhraní pro nastavení.

---

## Jak to funguje (Architektura)

Aplikace je navržena tak, aby byla co nejefektivnější a reagovala rychle. Zde je zjednodušený popis její vnitřní architektury:

1.  **Detekce aktivační fráze:** Po spuštění aplikace neustále naslouchá v úsporném režimu (`SpeechRecognitionService`). Neanalyzuje vše, co slyší, ale čeká pouze na jednu z vámi definovaných **aktivačních frází** (např. "Hey asistente").

2.  **Rozpoznání příkazu:** Jakmile je aktivační fráze rozpoznána, asistent se přepne do aktivního režimu a nahraje následující větu – váš příkaz.

3.  **Zpracování příkazu:** Rozpoznaný text je předán službě `AssistantService`, která jej porovná se seznamem vašich **akcí**. Hledá shodu mezi vysloveným příkazem a "spouštěcí frází" definovanou u každé akce.

4.  **Provedení akce:** Pokud je nalezena shoda, provede se příslušná akce:
    *   **Webhook:** Zavolá se zadaná URL adresa metodou `POST`. To je ideální pro ovládání chytré domácnosti (např. Home Assistant, IFTTT).
    *   **Tasker:** Odešle se příkaz (Intent) do aplikace Tasker ke spuštění konkrétní úlohy.

5.  **Ukládání nastavení:** Veškerá vaše konfigurace (aktivační fráze, akce, atd.) je trvale uložena přímo v úložišti aplikace na vašem telefonu. K tomu se využívá klíč-hodnota úložiště (`key-value store`) poskytované NativeScriptem (`ApplicationSettings`). To znamená, že vaše data zůstanou zachována i po restartu aplikace.

---

## Technologický stack

Tento projekt využívá následující technologie:

-   **[NativeScript](https://nativescript.org/)**: Framework pro vývoj nativních mobilních aplikací pro iOS a Android z jedné kódové základny.
-   **[TypeScript](https://www.typescriptlang.org/)**: Staticky typovaný nadmnožina JavaScriptu, která zvyšuje robustnost a usnadňuje údržbu kódu.
-   **[Tailwind CSS](https://tailwindcss.com/)**: "Utility-first" CSS framework pro rychlý a efektivní design uživatelského rozhraní.
-   **Android SpeechRecognizer**: Nativní API od Androidu pro převod řeči na text, které zajišťuje vysokou přesnost a efektivitu.

---

## Uživatelská příručka

### První spuštění

Při prvním spuštění vás aplikace požádá o **povolení k přístupu k mikrofonu**. Toto povolení je nezbytné pro rozpoznávání hlasu. Prosím, povolte ho.

Po udělení oprávnění přejde aplikace do pohotovostního režimu. Na hlavní obrazovce uvidíte stav "Čekám na aktivační frázi...".

### Základní použití

1.  **Aktivace asistenta:** Řekněte jednu z aktivačních frází. Výchozí fráze jsou "**Hey asistente**" nebo "**Pomoc**".
2.  **Vyslovení příkazu:** Po aktivační frázi se stav změní na "Poslouchám...". Nyní vyslovte svůj příkaz (např. "rozsviť světlo v obýváku").
3.  **Zpracování:** Asistent rozpozná váš příkaz, provede nastavenou akci a zobrazí výsledek. Poté se opět vrátí do pohotovostního režimu.

### Nastavení aplikace

Na hlavní obrazovce klepněte na tlačítko **"Nastavení"** pro konfiguraci aplikace.

#### 1. Správa akcí

Zde definujete, co má asistent dělat.

-   **Přidání nové akce:**
    1.  **Název:** Pojmenujte si akci (např. "Světla v kuchyni").
    2.  **Spouštěcí fráze:** Napište frázi, kterou chcete akci spustit (např. "rozsviť v kuchyni"). Asistent hledá tuto frázi ve vašem příkazu, takže nemusí být přesná.
    3.  **Typ akce:** Vyberte si jednu ze dvou možností:
        -   **Webhook:** Pro volání webové adresy (URL).
            -   Do pole **"URL adresa webhooku"** vložte celou adresu, která se má zavolat.
        -   **Tasker:** Pro spuštění úlohy ve specifické aplikaci **Tasker**.
            -   Do pole **"Název úlohy v Taskeru"** napište **přesný název** úlohy, jak ji máte pojmenovanou v aplikaci Tasker.
    4.  Klepněte na **"Přidat akci"**.

-   **Seznam akcí:**
    -   Pod formulářem vidíte seznam všech vašich nastavených akcí.
    -   Pro smazání akce klepněte na tlačítko **"Odstranit"** vedle ní.

#### 2. Další nastavení

-   **Aktivační fráze:** Spravujte seznam frází, na které bude asistent reagovat.
-   **Zvuková zpětná vazba:** Zapněte nebo vypněte zvuky, které signalizují začátek a konec nahrávání.

---

## Požadavky

### Integrace s Taskerem

-   Abyste mohli používat akce typu "Tasker", musíte mít na svém telefonu nainstalovanou aplikaci **[Tasker](https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm)** od vývojáře joaomgcd.
-   V Taskeru musíte povolit externí kontrolu. V menu Taskeru jděte do `Preferences -> Misc -> Allow External Access` a ujistěte se, že je tato volba zaškrtnutá.

---

## Příručka pro vývojáře

Pokud chcete přispět do projektu nebo si aplikaci sami sestavit, postupujte podle následujících kroků.

### Požadavky pro vývoj

-   **[Node.js](https://nodejs.org/)**: Ujistěte se, že máte nainstalovanou aktuální LTS verzi.
-   **NativeScript CLI**: Nainstalujte jej globálně pomocí příkazu:
    ```bash
    npm install -g nativescript
    ```
-   **Android Studio**: Pro nastavení Android SDK a emulátoru. Sledujte oficiální [instrukce pro nastavení NativeScriptu](https://docs.nativescript.org/environment-setup.html#android-setup).

### Instalace a spuštění

1.  **Klonování repozitáře:**
    ```bash
    git clone https://github.com/TestujuJa/CZE-asistent.git
    cd CZE-asistent
    ```

2.  **Instalace závislostí:**
    ```bash
    npm install
    ```

3.  **Spuštění na zařízení nebo emulátoru:**
    Připojte své Android zařízení nebo spusťte emulátor a poté spusťte příkaz:
    ```bash
    ns run android
    ```

### Struktura projektu

-   `app/`: Hlavní adresář s veškerým kódem aplikace.
    -   `app-root.xml`: Kořenové zobrazení aplikace.
    -   `main-page.xml` / `main-page.ts`: Hlavní stránka aplikace a její view-model.
    -   `settings-page.xml` / `settings-page.ts`: Stránka s nastavením a její view-model.
    -   `services/`: Oddělená logika pro různé funkce (rozpoznávání řeči, správa nastavení, atd.).
    -   `assets/`: Statické soubory, jako jsou zvuky.
-   `App_Resources/`: Specifické zdroje pro platformu Android (ikony, manifest, atd.).
-   `nativescript.config.ts`: Konfigurační soubor pro NativeScript.
-   `package.json`: Seznam závislostí a skriptů projektu.

---

[Edit in StackBlitz ⚡️][def]

[def]: https://stackblitz.com/~/github.com/TestujuJa/CZE-asistent
