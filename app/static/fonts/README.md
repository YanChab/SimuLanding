# static/fonts/ — Polices auto-hébergées

Ce dossier contient les fichiers de polices hébergées localement par l'application.

## Fichiers attendus

| Fichier | Police | Usage |
|---------|--------|-------|
| `roboto-regular.woff2` | Roboto Regular (400) | Corps de texte |
| `roboto-regular.woff` | Roboto Regular (400) | Fallback navigateurs anciens |
| `roboto-medium.woff2` | Roboto Medium (500) | Texte semi-gras |
| `roboto-medium.woff` | Roboto Medium (500) | Fallback navigateurs anciens |
| `roboto-bold.woff2` | Roboto Bold (700) | Texte gras |
| `roboto-bold.woff` | Roboto Bold (700) | Fallback navigateurs anciens |
| `eurostile-bold.woff2` | Eurostile Bold | Titres (h1, h2, h3…) |
| `eurostile-bold.woff` | Eurostile Bold | Fallback navigateurs anciens |
| `freshbot.woff2` | Freshbot | Logo « SuiviProcess » |
| `freshbot.woff` | Freshbot | Fallback navigateurs anciens |

## Comment ajouter les fichiers

1. Obtenir les fichiers de police Eurostile Bold et Freshbot (formats `.woff2` et `.woff`).
2. Les placer dans ce dossier (`static/fonts/`).
3. Lancer `python manage.py collectstatic` en production.

> **Note** : toutes les polices sont auto-hébergées pour garantir le fonctionnement hors-ligne.
> Les fichiers Roboto `.woff2` peuvent être téléchargés depuis [Google Fonts](https://fonts.google.com/specimen/Roboto) (bouton Download family → extraire les `.ttf` puis convertir).

## Conversion de formats

Si vous disposez des polices au format `.ttf` ou `.otf`, vous pouvez les convertir :

- En ligne : [transfonter.org](https://transfonter.org/) ou [fontsquirrel.com/tools/webfont-generator](https://www.fontsquirrel.com/tools/webfont-generator)  
- En CLI : `woff2_compress font.ttf` (paquet `woff2`)
