"""Catalogue des messages.

Une entrée par message, deux langues obligatoires. Les tests vérifient qu'aucune
clé n'est orpheline et que les deux langues attendent les mêmes variables.
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # ---- device -----------------------------------------------------------
    "device.not_found": {
        "en": "No iPhone detected. Plug it in over USB, unlock it, and tap "
              "“Trust” when asked to pair.",
        "fr": "Aucun iPhone détecté. Branche-le en USB, déverrouille-le, "
              "et réponds « Se fier » à la demande d'appairage.",
    },
    "device.not_paired": {
        "en": "iPhone detected but not paired. Unlock the screen, then accept "
              "“Trust This Computer”.",
        "fr": "iPhone détecté mais non appairé. Déverrouille l'écran puis "
              "accepte « Se fier à cet ordinateur ».",
    },
    "device.connect_failed": {
        "en": "Cannot connect: {detail}",
        "fr": "Connexion impossible : {detail}",
    },
    "device.storage_failed": {
        "en": "Cannot read storage: {detail}",
        "fr": "Lecture du stockage impossible : {detail}",
    },
    "device.unexpected_domain": {
        "en": "Unexpected response from the com.apple.disk_usage domain.",
        "fr": "Réponse inattendue du domaine com.apple.disk_usage.",
    },
    "device.disconnected": {
        "en": "The iPhone was disconnected during the operation.\n"
              "  Plug it back in, unlock it, and run the command again. What "
              "was already processed is done; the rest was not.",
        "fr": "L'iPhone a été déconnecté pendant l'opération.\n"
              "  Rebranche-le, déverrouille-le, puis relance la commande. Ce qui "
              "a déjà été traité l'est définitivement ; le reste ne l'a pas été.",
    },
    "device.refused": {
        "en": "The device refused an operation: {name}.\n"
              "  Check that it is unlocked and paired, then try again.",
        "fr": "L'appareil a refusé une opération : {name}.\n"
              "  Vérifie qu'il est déverrouillé et appairé, puis réessaie.",
    },

    # ---- battery ----------------------------------------------------------
    "battery.verdict.worn": {
        "en": "Worn battery. This is the number one cause of slowness on an "
              "older device: iOS throttles the CPU to prevent shutdowns. "
              "Replacing the battery buys back more performance than any "
              "amount of file cleaning.",
        "fr": "Batterie usée. C'est la première cause de lenteur sur un "
              "appareil ancien : iOS bride le processeur pour éviter les "
              "extinctions. Un remplacement de batterie rend plus de "
              "performance que n'importe quel nettoyage de fichiers.",
    },
    "battery.verdict.aging": {
        "en": "Ageing battery, still within tolerance. Keep an eye on it: "
              "below 80 % health, throttling becomes likely.",
        "fr": "Batterie vieillissante mais encore dans les clous. Surveille : "
              "sous 80 % de santé, le bridage devient probable.",
    },
    "battery.verdict.healthy": {
        "en": "Battery in good shape. If the device feels slow, the cause is "
              "elsewhere.",
        "fr": "Batterie en bon état. La lenteur, s'il y en a, vient d'ailleurs.",
    },
    "battery.label.health": {"en": "Health", "fr": "Santé"},
    "battery.label.cycles": {"en": "Cycles", "fr": "Cycles"},
    "battery.label.charge": {"en": "Charge", "fr": "Charge"},
    "battery.label.temperature": {"en": "Temperature", "fr": "Température"},
    "battery.cycles_detail": {
        "en": "{pct} % of the {rated} cycles Apple rates this model for",
        "fr": "{pct} % des {rated} cycles prévus par Apple",
    },
    "battery.unavailable": {
        "en": "Battery counters unavailable on this device.",
        "fr": "Compteurs de batterie indisponibles sur cet appareil.",
    },
    "battery.settings_hint": {
        "en": "Settings > Battery > Battery Health tells you whether "
              "performance management is active on this device.",
        "fr": "Réglages > Batterie > État de la batterie indique si la gestion "
              "des performances est active sur cet appareil.",
    },

    # ---- rules ------------------------------------------------------------
    "rule.media_analysis.title": {
        "en": "Image-analysis backups",
        "fr": "Sauvegardes d'analyse d'images",
    },
    "rule.media_analysis.detail": {
        "en": "Backup copies of the photo-analysis databases (OCR, scenes). "
              "iOS regenerates them in the background.",
        "fr": "Copies de secours des bases d'analyse photo (OCR, scènes). "
              "iOS les régénère en tâche de fond.",
    },
    "rule.media_analysis.action": {
        "en": "Safe to delete. Analysis re-runs on the next charge.",
        "fr": "Supprimable. L'analyse photo se refera à la prochaine charge.",
    },
    "rule.thumbnails.title": {
        "en": "Photo library thumbnails",
        "fr": "Vignettes de la photothèque",
    },
    "rule.thumbnails.detail": {
        "en": "{size} of pre-computed thumbnails.",
        "fr": "{size} de vignettes pré-calculées.",
    },
    "rule.thumbnails.action": {
        "en": "Do not delete by hand: iOS rebuilds them by heating the phone "
              "for hours, with no lasting gain.",
        "fr": "Ne pas supprimer à la main : iOS les reconstruit en chauffant "
              "le téléphone pendant des heures, sans gain durable.",
    },
    "rule.downloads.title": {
        "en": "Forgotten downloads",
        "fr": "Téléchargements oubliés",
    },
    "rule.downloads.detail": {
        "en": "{count} files untouched for more than {days} days.",
        "fr": "{count} fichiers non touchés depuis plus de {days} jours.",
    },
    "rule.temp.title": {"en": "Temporary files", "fr": "Fichiers temporaires"},
    "rule.temp.detail": {
        "en": "Leftovers from interrupted transfers.",
        "fr": "Restes de transferts interrompus.",
    },
    "rule.sidecar.title": {
        "en": "Orphaned edit sidecars",
        "fr": "Fichiers de retouche orphelins",
    },
    "rule.sidecar.detail": {
        "en": "{count} .AAE files whose original photo no longer exists.",
        "fr": "{count} fichiers .AAE dont la photo d'origine n'existe plus.",
    },
    "rule.deletable": {"en": "Safe to delete.", "fr": "Supprimable."},
    "rule.music.title": {
        "en": "Offline music",
        "fr": "Musique téléchargée hors-ligne",
    },
    "rule.music.detail": {
        "en": "{size} of audio stored locally.",
        "fr": "{size} d'audio stocké localement.",
    },
    "rule.music.action": {
        "en": "Immediate gain if you stream: Settings > Music > Downloads. Do "
              "not delete over AFC (it breaks the library) — use the Music app.",
        "fr": "Gain immédiat si tu streames : Réglages > Musique > "
              "Téléchargements. Ne pas supprimer par AFC (casse la "
              "bibliothèque) — passe par l'app Musique.",
    },
    "rule.video.title": {
        "en": "Downloaded podcasts and purchases",
        "fr": "Podcasts et achats téléchargés",
    },
    "rule.video.detail": {
        "en": "{size} of re-downloadable content.",
        "fr": "{size} de contenu re-téléchargeable.",
    },
    "rule.video.action": {
        "en": "Clear it from the app that downloaded it.",
        "fr": "À purger depuis l'app concernée.",
    },
    "rule.bigvideo.title": {
        "en": "Large old videos",
        "fr": "Grosses vidéos anciennes",
    },
    "rule.bigvideo.detail": {
        "en": "{count} videos over {size}, older than {months} months.",
        "fr": "{count} vidéos de plus de {size}, vieilles de plus de {months} mois.",
    },
    "rule.bigvideo.action": {
        "en": "Copy them to the Mac, then delete them from the Photos app — "
              "never over AFC.",
        "fr": "Copie-les sur le Mac, puis supprime-les depuis l'app Photos — "
              "jamais par AFC.",
    },
    "rule.app_bloat.title": {
        "en": "Apps bloated by their data",
        "fr": "Applications gonflées par leurs données",
    },
    "rule.app_bloat.detail": {
        "en": "{count} apps whose data outweighs their code: {list}.",
        "fr": "{count} apps où les données dépassent le code : {list}.",
    },
    "rule.app_bloat.action": {
        "en": "Clear the cache inside the app, or uninstall and reinstall: the "
              "binary re-downloads, the cache does not.",
        "fr": "Vide le cache dans l'app, ou désinstalle/réinstalle : "
              "le binaire se retélécharge, le cache non.",
    },
    "rule.heavy_apps.title": {
        "en": "Apps over 1 GB",
        "fr": "Applications de plus d'1 Go",
    },
    "rule.heavy_apps.action": {
        "en": "Offload the ones you no longer open: Settings > General > "
              "iPhone Storage.",
        "fr": "Décharge celles que tu n'ouvres plus : Réglages > "
              "Général > Stockage iPhone.",
    },
    "rule.crash.title": {"en": "Crash reports", "fr": "Rapports de plantage"},
    "rule.crash.detail": {
        "en": "{count} reports accumulated by iOS.",
        "fr": "{count} rapports accumulés par iOS.",
    },
    "rule.crash.action": {
        "en": "“ipsd clean --crash” archives them to the Mac, then erases them.",
        "fr": "« ipsd clean --crash » les archive sur le Mac puis les efface.",
    },

    # ---- purge risks ------------------------------------------------------
    "purge.risk.2fa": {
        "en": "Two-factor codes stored locally: you may lose access to your "
              "accounts. Export them first.",
        "fr": "Codes à deux facteurs stockés localement : tu peux perdre "
              "l'accès à tes comptes. Exporte-les d'abord.",
    },
    "purge.risk.messaging": {
        "en": "Conversation history stored on the device. Lost without a "
              "prior backup.",
        "fr": "Historique de conversations stocké sur l'appareil. Perdu sans "
              "sauvegarde préalable.",
    },
    "purge.risk.wallet": {
        "en": "Local private keys / recovery phrase. Funds are lost for good "
              "without the seed.",
        "fr": "Clés privées / phrase de récupération locales. Perte définitive "
              "des fonds sans la seed.",
    },
    "purge.risk.editor": {
        "en": "Unsynced projects and edits stored locally.",
        "fr": "Projets et retouches non synchronisés stockés localement.",
    },
    "purge.risk.notes": {
        "en": "Notes and documents that may exist only on the device.",
        "fr": "Notes et documents potentiellement locaux uniquement.",
    },
    "purge.risk.health": {
        "en": "Activity or health history sometimes stored only locally.",
        "fr": "Historique d'activité ou de santé parfois local uniquement.",
    },

    # ---- report -----------------------------------------------------------
    "report.device": {"en": "Device", "fr": "Appareil"},
    "report.battery_short": {"en": "battery", "fr": "batterie"},
    "report.where.title": {"en": "Where the space went", "fr": "O\u00f9 part la place"},
    "report.col.item": {"en": "Item", "fr": "Poste"},
    "report.col.size": {"en": "Size", "fr": "Taille"},
    "report.col.pct_used": {"en": "% used", "fr": "% utilis\u00e9"},
    "report.col.source": {"en": "Source", "fr": "Source"},
    "report.row.apps": {
        "en": "Applications (code + data)",
        "fr": "Applications (code + donn\u00e9es)",
    },
    "report.row.media": {
        "en": "Reachable media volume",
        "fr": "Volume m\u00e9dia accessible",
    },
    "report.row.unattributed": {
        "en": "Unattributed / \u201cSystem Data\u201d",
        "fr": "Non attribu\u00e9 / \u00ab Donn\u00e9es syst\u00e8me \u00bb",
    },
    "report.row.total": {"en": "Total used", "fr": "Total occup\u00e9"},
    "report.source.deduction": {"en": "deduction", "fr": "d\u00e9duction"},
    "report.free.capacity": {"en": "Data capacity", "fr": "Capacit\u00e9 donn\u00e9es"},
    "report.free.used": {"en": "Used", "fr": "Occup\u00e9"},
    "report.free.free": {"en": "Free right now", "fr": "Libre imm\u00e9diatement"},
    "report.free.purgeable": {
        "en": "Freeable by iOS under pressure",
        "fr": "Lib\u00e9rable par iOS sous pression",
    },
    "report.free.purgeable_hint": {
        "en": "(caches iOS will sacrifice on its own)",
        "fr": "(caches qu'iOS sacrifiera seul)",
    },
    "report.unattributed_note": {
        "en": "The \u201cunattributed\u201d figure is large. It covers iOS itself, "
              "system and iCloud caches, out of reach of a USB connection "
              "without a jailbreak. No tool can break it down.",
        "fr": "Le poste \u00ab non attribu\u00e9 \u00bb est important. Il couvre iOS "
              "lui-m\u00eame, les caches syst\u00e8me et iCloud, hors de port\u00e9e d'une "
              "connexion USB sans jailbreak. Aucun outil ne peut le d\u00e9tailler.",
    },
    "report.breakdown_hint": {
        "en": "Breakdown by item: run [bold]ipsd doctor[/bold].",
        "fr": "Ventilation par poste : lance [bold]ipsd doctor[/bold].",
    },
    "report.findings.title": {"en": "Findings", "fr": "Constats"},
    "report.col.level": {"en": "Level", "fr": "Niveau"},
    "report.col.finding": {"en": "Finding", "fr": "Constat"},
    "report.col.what": {"en": "What to do", "fr": "Que faire"},
    "report.nothing": {"en": "Nothing to report.", "fr": "Rien \u00e0 signaler."},
    "report.reclaimable": {"en": "Reclaimable safely:", "fr": "R\u00e9cup\u00e9rable sans risque :"},
    "report.arbitrable": {"en": "Your call:", "fr": "Sur arbitrage :"},
    "tier.safe": {"en": "SAFE", "fr": "S\u00dbR"},
    "tier.review": {"en": "YOUR CALL", "fr": "\u00c0 ARBITRER"},
    "tier.manual": {"en": "MANUAL", "fr": "MANUEL"},
    "report.apps.title": {"en": "Top {limit} applications", "fr": "Top {limit} applications"},
    "report.col.app": {"en": "Application", "fr": "Application"},
    "report.col.total": {"en": "Total", "fr": "Total"},
    "report.col.code": {"en": "Code", "fr": "Code"},
    "report.col.data": {"en": "Data", "fr": "Donn\u00e9es"},
    "report.col.data_share": {"en": "Data share", "fr": "Part donn\u00e9es"},

    # ---- action plan ------------------------------------------------------
    "actions.title": {
        "en": "What I can do right now",
        "fr": "Ce que je peux faire maintenant",
    },
    "actions.none": {
        "en": "Nothing to do. The device is clean.",
        "fr": "Rien \u00e0 faire. L'appareil est propre.",
    },
    "actions.kind.auto": {"en": "NO RISK", "fr": "SANS RISQUE"},
    "actions.kind.choice": {"en": "YOUR CALL", "fr": "TON CHOIX"},
    "actions.kind.external": {"en": "OUTSIDE THIS TOOL", "fr": "HORS OUTIL"},
    "actions.reclaim_now": {
        "en": "Reclaimable with nothing lost:",
        "fr": "R\u00e9cup\u00e9rable sans rien perdre :",
    },
    "actions.reclaim_total": {
        "en": "Total if you go all the way:",
        "fr": "Au total si tu vas au bout :",
    },
    "action.clean.title": {
        "en": "Clean regenerable caches",
        "fr": "Nettoyer les caches r\u00e9g\u00e9n\u00e9rables",
    },
    "action.clean.why": {
        "en": "Analysis caches and crash reports. iOS rebuilds them on its own.",
        "fr": "Caches d'analyse et rapports de plantage. iOS les reconstruit seul.",
    },
    "action.clean.caveat": {
        "en": "Every file is copied to the Mac before being removed.",
        "fr": "Chaque fichier est copi\u00e9 sur le Mac avant d'\u00eatre retir\u00e9.",
    },
    "action.reinstall.title": {"en": "Reinstall {app}", "fr": "R\u00e9installer {app}"},
    "action.reinstall.why": {
        "en": "{app} carries {data} of data for {code} of code.",
        "fr": "{app} porte {data} de donn\u00e9es pour {code} de code.",
    },
    "action.reinstall.caveat": {
        "en": "You will have to sign in again. The app re-downloads from the "
              "App Store.",
        "fr": "Tu devras te reconnecter. L'app se ret\u00e9l\u00e9charge depuis l'App Store.",
    },
    "action.battery.title": {
        "en": "Have the battery replaced",
        "fr": "Faire remplacer la batterie",
    },
    "action.battery.why": {
        "en": "Health {health} %, {cycles} cycles. iOS throttles the CPU below 80 %.",
        "fr": "Sant\u00e9 {health} %, {cycles} cycles. iOS bride le processeur en "
              "dessous de 80 %.",
    },
    "action.battery.caveat": {
        "en": "This is the only move that gives speed back. No amount of file "
              "cleaning will.",
        "fr": "C'est le seul geste qui rend de la vitesse. Aucun nettoyage de "
              "fichiers n'y changera rien.",
    },
    "action.lowspace.title": {
        "en": "Get above the critical space threshold",
        "fr": "Descendre sous le seuil critique d'espace",
    },
    "action.lowspace.why": {
        "en": "Only {pct} % of space is free. Below 10 %, APFS runs out of room "
              "and everything slows down.",
        "fr": "Il reste {pct} % d'espace libre. Sous 10 %, APFS n'a plus de "
              "marge et tout ralentit.",
    },
    "action.lowspace.caveat": {
        "en": "This is the one case where freeing space genuinely speeds up "
              "the device.",
        "fr": "C'est le seul cas o\u00f9 lib\u00e9rer de la place acc\u00e9l\u00e8re r\u00e9ellement "
              "l'appareil.",
    },

    # ---- levels -----------------------------------------------------------
    "levels.title": {
        "en": "Three cleaning levels",
        "fr": "Trois niveaux de nettoyage",
    },
    "levels.free_after": {"en": "{before} \u2192 {after} free", "fr": "{before} \u2192 {after} libres"},
    "levels.simple.title": {"en": "Simple", "fr": "Simple"},
    "levels.simple.promise": {
        "en": "Regenerable caches and crash reports.",
        "fr": "Caches r\u00e9g\u00e9n\u00e9rables et rapports de plantage.",
    },
    "levels.simple.cost": {
        "en": "Nothing lost. iOS rebuilds it all.",
        "fr": "Aucune perte. iOS reconstruit tout seul.",
    },
    "levels.advanced.title": {"en": "Advanced", "fr": "Avanc\u00e9"},
    "levels.advanced.promise": {
        "en": "The simple level, plus reinstalling the most bloated apps.",
        "fr": "Le simple, plus la r\u00e9installation des apps les plus gonfl\u00e9es.",
    },
    "levels.advanced.cost": {
        "en": "Sign in again on those apps. Nothing irreplaceable.",
        "fr": "Reconnexion n\u00e9cessaire sur ces apps. Rien d'irrempla\u00e7able.",
    },
    "levels.maximum.title": {"en": "Maximum", "fr": "Maximum"},
    "levels.maximum.promise": {
        "en": "Every re-downloadable app with no unique local data.",
        "fr": "Toutes les apps re-t\u00e9l\u00e9chargeables sans donn\u00e9es locales uniques.",
    },
    "levels.maximum.cost": {
        "en": "Sign in again on each app concerned.",
        "fr": "Reconnexion sur chaque app concern\u00e9e.",
    },
    "levels.footer": {
        "en": "No level touches photos, iOS databases, or apps holding unique\n"
              " data (2FA, messengers, photo editors).\n"
              " Every deletion is confirmed by you before it runs.",
        "fr": "Aucun niveau ne touche aux photos, aux bases iOS, ni aux apps\n"
              " porteuses de donn\u00e9es uniques (2FA, messageries, \u00e9diteurs photo).\n"
              " Chaque suppression est confirm\u00e9e par toi avant ex\u00e9cution.",
    },

    # ---- CLI --------------------------------------------------------------
    "cli.interrupted": {"en": "Interrupted.", "fr": "Interrompu."},
    "cli.lang.prompt": {
        "en": "Choose your language / Choisis ta langue",
        "fr": "Choisis ta langue / Choose your language",
    },
    "cli.lang.saved": {
        "en": "Language set to English. Change it any time with: ipsd lang",
        "fr": "Langue r\u00e9gl\u00e9e sur le fran\u00e7ais. Modifiable \u00e0 tout moment : ipsd lang",
    },
    "cli.lang.current": {"en": "Current language: {lang}", "fr": "Langue actuelle : {lang}"},
    "cli.no_device": {
        "en": "No device. Plug in the iPhone and unlock it.",
        "fr": "Aucun appareil. Branche l'iPhone et d\u00e9verrouille-le.",
    },
    "cli.status.apps": {
        "en": "Measuring applications\u2026",
        "fr": "Mesure des applications\u2026",
    },
    "cli.status.apps_slow": {
        "en": "Measuring applications (about 30 s)\u2026",
        "fr": "Mesure des applications (peut prendre ~30 s)\u2026",
    },
    "cli.status.media": {
        "en": "Walking the media volume\u2026",
        "fr": "Parcours du volume m\u00e9dia\u2026",
    },
    "cli.status.media_count": {
        "en": "Walking the media volume\u2026 {count} files",
        "fr": "Parcours du volume m\u00e9dia\u2026 {count} fichiers",
    },
    "cli.status.searching": {
        "en": "Looking for reclaimable files\u2026",
        "fr": "Recherche des fichiers r\u00e9cup\u00e9rables\u2026",
    },
    "cli.status.uninstalling": {"en": "Uninstalling\u2026", "fr": "D\u00e9sinstallation\u2026"},
    "cli.apps.total": {
        "en": "{count} applications, [bold]{size}[/bold] in total.",
        "fr": "{count} applications, [bold]{size}[/bold] au total.",
    },
    "cli.scan.summary": {
        "en": "{count} files walked in {seconds} s",
        "fr": "{count} fichiers parcourus en {seconds} s",
    },
    "cli.scan.errors": {
        "en": ", {count} unreadable directories",
        "fr": ", {count} dossiers illisibles",
    },
    "cli.confirm.header": {
        "en": "[bold]{count} files[/bold] ({size}) will be deleted from the "
              "iPhone: {what}.",
        "fr": "[bold]{count} fichiers[/bold] ({size}) seront supprim\u00e9s de "
              "l'iPhone : {what}.",
    },
    "cli.confirm.copy_note": {
        "en": "A copy is made on the Mac first.",
        "fr": "Une copie est faite sur le Mac au pr\u00e9alable.",
    },
    "cli.confirm.question": {
        "en": "Confirm deletion?",
        "fr": "Confirmer la suppression ?",
    },
    "cli.confirm.no_tty": {
        "en": "Deletion cancelled: no interactive terminal to ask for "
              "confirmation.\n  Add --yes if you are running this from a script.",
        "fr": "Suppression annul\u00e9e : pas de terminal interactif pour demander "
              "confirmation.\n  Ajoute --yes si tu ex\u00e9cutes la commande depuis "
              "un script.",
    },
    "cli.cancelled": {
        "en": "Cancelled. Nothing was deleted.",
        "fr": "Annul\u00e9. Rien n'a \u00e9t\u00e9 supprim\u00e9.",
    },
    "cli.clean.nothing": {"en": "Nothing to clean.", "fr": "Rien \u00e0 nettoyer."},
    "cli.clean.dry_run": {
        "en": "Dry run. {count} files, [bold]{size}[/bold] would be freed.",
        "fr": "Simulation. {count} fichiers, [bold]{size}[/bold] seraient lib\u00e9r\u00e9s.",
    },
    "cli.clean.rerun": {
        "en": "Run again with --apply to execute.",
        "fr": "Relance avec --apply pour ex\u00e9cuter.",
    },
    "cli.clean.done": {
        "en": "{count} files deleted, [bold]{size}[/bold] freed.",
        "fr": "{count} fichiers supprim\u00e9s, [bold]{size}[/bold] lib\u00e9r\u00e9s.",
    },
    "cli.clean.backup": {"en": "Safety copy: {path}", "fr": "Copie de s\u00e9curit\u00e9 : {path}"},
    "cli.crash.none": {"en": "No crash reports.", "fr": "Aucun rapport de plantage."},
    "cli.crash.dry_run": {
        "en": "Dry run. {count} reports would be archived.",
        "fr": "Simulation. {count} rapports \u00e0 archiver.",
    },
    "cli.crash.kept": {
        "en": "Crash reports kept.",
        "fr": "Rapports de plantage conserv\u00e9s.",
    },
    "cli.crash.done": {
        "en": "{count} reports archived to {path} ({size}), then erased.",
        "fr": "{count} rapports archiv\u00e9s dans {path} ({size}) puis effac\u00e9s.",
    },
    "cli.crash.label": {"en": "crash reports", "fr": "rapports de plantage"},
    "cli.purge.title": {
        "en": "Uninstall candidates",
        "fr": "Candidates \u00e0 la d\u00e9sinstallation",
    },
    "cli.purge.col.reclaimed": {"en": "Reclaimed", "fr": "R\u00e9cup\u00e9r\u00e9"},
    "cli.purge.col.of_data": {"en": "of which data", "fr": "dont donn\u00e9es"},
    "cli.purge.col.risk": {"en": "Risk", "fr": "Risque"},
    "cli.purge.no_match": {
        "en": "No app matches \u201c{term}\u201d.",
        "fr": "Aucune app ne correspond \u00e0 \u00ab {term} \u00bb.",
    },
    "cli.purge.below_threshold": {
        "en": "No app is above the threshold.",
        "fr": "Aucune app ne d\u00e9passe le seuil.",
    },
    "cli.purge.estimate": {
        "en": "Estimated gain: [bold]{size}[/bold] across {count} app(s).",
        "fr": "Gain estim\u00e9 : [bold]{size}[/bold] sur {count} app(s).",
    },
    "cli.purge.excluded": {
        "en": "{count} app(s) excluded for risk of data loss.",
        "fr": "{count} app(s) \u00e9cart\u00e9e(s) pour risque de perte de donn\u00e9es.",
    },
    "cli.purge.force_hint": {
        "en": "--force-risky to override, at your own risk.",
        "fr": "--force-risky pour passer outre, \u00e0 tes risques.",
    },
    "cli.purge.untouched": {
        "en": "Dry run. Nothing was touched.",
        "fr": "Simulation. Rien n'a \u00e9t\u00e9 touch\u00e9.",
    },
    "cli.purge.add_apply": {
        "en": "Add --apply to uninstall.",
        "fr": "Ajoute --apply pour d\u00e9sinstaller.",
    },
    "cli.purge.nothing": {
        "en": "Nothing to uninstall.",
        "fr": "Rien \u00e0 d\u00e9sinstaller.",
    },
    "cli.purge.warning": {
        "en": "The local data of these apps will be erased permanently.",
        "fr": "Les donn\u00e9es locales de ces apps seront effac\u00e9es d\u00e9finitivement.",
    },
    "cli.purge.rebuy": {
        "en": "The binary will re-download from the App Store.",
        "fr": "Le binaire se ret\u00e9l\u00e9chargera depuis l'App Store.",
    },
    "cli.purge.confirm_word": {"en": "DELETE", "fr": "SUPPRIMER"},
    "cli.purge.confirm_prompt": {
        "en": "Type {word} to confirm",
        "fr": "Tape {word} pour confirmer",
    },
    "cli.purge.done": {
        "en": "{count} app(s) uninstalled, estimated [bold]{size}[/bold].",
        "fr": "{count} app(s) d\u00e9sinstall\u00e9e(s), estimation [bold]{size}[/bold].",
    },
    "cli.purge.measured": {
        "en": "Free space measured: {before} \u2192 [bold]{after}[/bold] (+{delta})",
        "fr": "Espace libre mesur\u00e9 : {before} \u2192 [bold]{after}[/bold] (+{delta})",
    },
    "cli.purge.spared": {"en": "{name} spared \u2014 {reason}", "fr": "{name} \u00e9pargn\u00e9e \u2014 {reason}"},
    "cli.boost.before": {"en": "Before", "fr": "Avant"},
    "cli.boost.cleaning": {"en": "Cleaning", "fr": "Nettoyage"},
    "cli.boost.after": {"en": "After", "fr": "Apr\u00e8s"},
    "cli.boost.free": {"en": "Free space", "fr": "Espace libre"},
    "cli.boost.used": {"en": "Used space", "fr": "Espace occup\u00e9"},
    "cli.boost.battery": {"en": "Battery health", "fr": "Sant\u00e9 batterie"},
    "cli.boost.crashes": {"en": "Crash reports", "fr": "Rapports de plantage"},
    "cli.boost.delta": {"en": "Change", "fr": "\u00c9cart"},
    "cli.boost.removed": {
        "en": "{count} files deleted ({size} of content removed).",
        "fr": "{count} fichiers supprim\u00e9s ({size} de contenu retir\u00e9).",
    },
    "cli.boost.crash_done": {
        "en": "Crash reports \u2014 {count} archived then erased",
        "fr": "Rapports de plantage \u2014 {count} archiv\u00e9s puis effac\u00e9s",
    },
    "cli.purgeable.free_now": {"en": "Free right now", "fr": "Libre imm\u00e9diatement"},
    "cli.purgeable.under_pressure": {
        "en": "Freeable under pressure",
        "fr": "Lib\u00e9rable sous pression",
    },
    "cli.purgeable.what": {
        "en": "[bold]What it is.[/bold] iOS keeps caches it knows it can "
              "sacrifice when a write runs short of room: thumbnails, local "
              "iCloud copies, search indexes, app data marked as disposable.",
        "fr": "[bold]Ce que c'est.[/bold] iOS garde des caches qu'il sait "
              "sacrifier seul quand une \u00e9criture manque de place : vignettes, "
              "copies iCloud locales, index de recherche, donn\u00e9es d'apps "
              "marqu\u00e9es jetables.",
    },
    "cli.purgeable.why": {
        "en": "[bold]Why it cannot be broken down.[/bold] No USB-reachable "
              "service exposes it. Verified on this device: the "
              "com.apple.mobile.storage domain returns empty, mobilegestalt "
              "storage keys are refused (DeprecationError), and NANDInfo is a "
              "binary blob from the flash controller \u2014 wear and blocks, not a "
              "breakdown.",
        "fr": "[bold]Pourquoi on ne peut pas le d\u00e9tailler.[/bold] Aucun service "
              "accessible en USB ne l'expose. V\u00e9rifi\u00e9 sur cet appareil : le "
              "domaine com.apple.mobile.storage renvoie vide, les cl\u00e9s "
              "mobilegestalt de stockage sont refus\u00e9es (DeprecationError), et "
              "NANDInfo est un blob binaire du contr\u00f4leur flash \u2014 usure et "
              "blocs, pas une ventilation.",
    },
    "cli.purgeable.advice": {
        "en": "[bold]What to do about it.[/bold] Nothing. That space frees "
              "itself the moment the system needs it. A product promising to "
              "\u201creclaim\u201d those bytes is selling you a cleanup iOS already does.",
        "fr": "[bold]Ce qu'il faut en faire.[/bold] Rien. Cet espace se lib\u00e8re "
              "tout seul au moment o\u00f9 le syst\u00e8me en a besoin. Un outil qui te "
              "promet de \u00ab r\u00e9cup\u00e9rer \u00bb ces octets te vend un nettoyage qu'iOS "
              "fait d\u00e9j\u00e0.",
    },
    "cli.trend.first": {
        "en": "First snapshot saved: [dim]{path}[/dim]\nRun [bold]ipsd trend[/bold] "
              "again in a few days to see the drift.",
        "fr": "Premier instantan\u00e9 enregistr\u00e9 : [dim]{path}[/dim]\nRelance "
              "[bold]ipsd trend[/bold] dans quelques jours pour voir la d\u00e9rive.",
    },
    "cli.trend.since": {
        "en": "Since {date} ({days} d): free space {before} \u2192 [bold]{after}[/bold]",
        "fr": "Depuis le {date} ({days} j) : espace libre {before} \u2192 [bold]{after}[/bold]",
    },
    "cli.trend.stable": {
        "en": "No app changed size.",
        "fr": "Aucune app n'a chang\u00e9 de taille.",
    },
    "cli.trend.col.change": {"en": "Change", "fr": "Variation"},
    "cli.trend.saved": {"en": "Snapshot saved: {path}", "fr": "Instantan\u00e9 enregistr\u00e9 : {path}"},
    "cli.restart.note": {
        "en": "A reboot frees up RAM and purges temporary files. The effect on "
              "disk space is small and temporary.",
        "fr": "Un red\u00e9marrage lib\u00e8re la m\u00e9moire vive et purge les fichiers "
              "temporaires. L'effet sur l'espace disque est faible et temporaire.",
    },
    "cli.restart.confirm": {
        "en": "Restart the iPhone now?",
        "fr": "Red\u00e9marrer l'iPhone maintenant ?",
    },
    "cli.restart.done": {"en": "Restart requested.", "fr": "Red\u00e9marrage demand\u00e9."},
}
