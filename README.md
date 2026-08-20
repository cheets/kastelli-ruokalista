# Kastelli ruokalista → RSS / iCal

Kastellin koulun ruokalista julkaistaan vain HTML-sivuna osoitteessa
<https://ravintolapalvelut.iss.fi/kastelli/>. Tämä projekti raapii sivun ja julkaisee
siitä **Aromi-yhteensopivan RSS-syötteen** ja **iCalendar-syötteen**, jotka esimerkiksi
Perhe.app osaa lukea.

## Syötteet

Kun GitHub Pages on käytössä (ks. alla):

- RSS: `https://<käyttäjä>.github.io/kastelli-ruokalista/menu.xml`
- iCal: `https://<käyttäjä>.github.io/kastelli-ruokalista/menu.ics`

Lisää RSS-osoite Perhe.appiin samaan tapaan kuin Aromi-syöte.

## Miten se toimii

| Tiedosto | Vastuu |
| --- | --- |
| `kastelli_menu/parser.py` | Poimii päivät, ateriaosiot ja ruokalajit ISS:n sivulta |
| `kastelli_menu/store.py` | Ylläpitää `data/menus.json`-arkistoa |
| `kastelli_menu/feeds.py` | Muodostaa `docs/menu.xml` ja `docs/menu.ics` |
| `kastelli_menu/build.py` | Ajaa koko ketjun |

ISS julkaisee kerrallaan vain **kuluvan viikon**. Siksi jokainen ajo tallentaa viikon
arkistoon, jolloin syötteessä on myös menneet päivät eikä yksittäinen epäonnistunut ajo
tyhjennä syötettä. Arkistosta säilytetään 60 päivää, syötteisiin poimitaan 14 päivää
taaksepäin ja kaikki tuleva.

Lähde ei julkaise ruoka-aikoja (jokaisella luokalla on oma vuoro) eikä
dieettimerkintöjä (`diets_container` on Kastellin osalta aina tyhjä), joten niitä ei ole
syötteissäkään.

## Käyttöönotto

1. Luo julkinen GitHub-repo ja työnnä tämä hakemisto sinne.
2. **Settings → Pages** → *Source: Deploy from a branch*, haara `main`, kansio `/docs`.
3. **Actions → Update menu feeds → Run workflow** ensimmäisen ajon käynnistämiseksi.
4. Tarkista, että `menu.xml` aukeaa Pages-osoitteesta, ja lisää se Perhe.appiin.

Ajastus on `0 4 * * *` (04:00 UTC päivittäin) tiedostossa
`.github/workflows/update-feeds.yml`.

## Paikallinen ajo

```bash
python3 -m kastelli_menu.build
```

Testit (vain vakiokirjasto, ei verkkoa):

```bash
python3 -m unittest discover -s tests -t .
```

Jos ISS muuttaa sivunsa rakennetta, ajo kirjoittaa varoituksen ja workflow menee
punaiseksi sen sijaan että julkaisisi hiljaa tyhjän syötteen.
