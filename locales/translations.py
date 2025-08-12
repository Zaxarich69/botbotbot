# No imports required in this module
translations = {
    "en": {
        "welcome_photo": "👋 Welcome to CryptoLuck! A new chance to win every week.\n\nPlease choose your language to continue.",
        "choose_language": "🌐 Choose your language:",
        "language_set": "✅ Language switched to English.",

        "wallet_setup_prompt": "First, let's set up your payout wallet for <b>{currency_name}</b>. This is where you'll receive your prize if you win.\n\nPlease send your {currency_name} wallet address.",
        "invalid_wallet_address": "❌ Invalid {currency_name} wallet address format. Please check and send it again.",
        "wallet_saved": "✅ Your {currency_name} wallet has been saved:\n<code>{address}</code>\n\nNow you're ready to play!",
        "current_wallet": "👛 Your current {currency_name} wallet:\n<code>{address}</code>\n\nTo change it, send a new wallet address.",
        "no_wallet_set": "You have not set a {currency_name} wallet yet. Please set one to receive prizes.",

        "main_menu_text": "🍀 <b>Main Menu</b>\n\n🏦 <b>Current Bank:</b> ${bank:.2f}\n🎟️ <b>Your Tickets:</b> {tickets}\n\nChoose an option:",
        "buy_ticket_button": "🎟 Buy Tickets",
        "my_wallet_button": "👛 My Payout Wallet",
        "language_button": "🌐 Language",
        "channel_button": "📢 Announcements",
        "back_to_menu": "🔙 Back to Menu",

        "choose_payment_currency": "💸 Choose a currency to pay with:",
        "payment_creation_text": (
            "To buy <b>{tickets} ticket(s)</b>, please send <b>{amount} {currency}</b>\n\n"
            "To the address: <code>{address}</code>\n\n"
            "<i>This payment is valid for 10 minutes. After confirmation, your tickets will be automatically credited.</i>"
        ),
        "payment_failed": "❌ Failed to create payment. Please try again in a few minutes.",
        "payment_received_notification": "✅ Payment received! <b>{tickets} ticket(s)</b> have been added to your account. Good luck!",

        "winner_dm": "🎉 Congratulations! You have won <b>${prize:.2f}</b> in the weekly lottery!\n\nYour prize is being processed and will be sent to your wallet: <code>{wallet}</code>",
        "winner_dm_no_wallet": "🎉 Congratulations! You have won <b>${prize:.2f}</b>!\n\nPlease set up your payout wallet using the menu. An admin will contact you shortly.",

        "admin_payout_notification": (
            "‼️ <b>MANUAL PAYOUT REQUIRED</b> ‼️\n\n"
            "Winner selected!\n\n"
            "<b>User:</b> {user_mention} (ID: <code>{user_id}</code>)\n"
            "<b>Prize:</b> ${prize:.2f}\n"
            "<b>Currency:</b> {currency_name}\n"
            "<b>Wallet:</b> <code>{wallet_address}</code>\n\n"
            "Please send the prize to this address."
        ),
        "draw_announcement_channel": (
            "🏆 <b>Weekly Draw Complete!</b> 🏆\n\n"
            "Prize of <b>${prize:.2f}</b> goes to user <code>...{user_id_part}</code>!\n\n"
            "🎉 Congratulations! 🎉\n\n"
            "<b>Total Collected:</b> ${total_collected:.2f}\n"
            "<b>Provably Fair Hash:</b> <code>{btc_hash}</code>\n\n"
            "New round has started. Good luck everyone!"
        ),
        "rollover_announcement_channel": (
            "⚠️ <b>Draw Postponed!</b> ⚠️\n\n"
            "Bank didn't reach ${min_bank:.2f} minimum.\n"
            "Collected ${bank:.2f} and all tickets roll over to next week.\n\n"
            "Keep participating! 🍀"
        ),
    },

    "es": {
        "welcome_photo": "👋 ¡Bienvenido a CryptoLuck! Una nueva oportunidad de ganar cada semana.\n\nPor favor elige tu idioma para continuar.",
        "choose_language": "🌐 Elige tu idioma:",
        "language_set": "✅ Idioma cambiado a Español.",

        "wallet_setup_prompt": "Primero, configuremos tu billetera de pago para <b>{currency_name}</b>. Aquí recibirás tu premio si ganas.\n\nPor favor envía tu dirección de billetera {currency_name}.",
        "invalid_wallet_address": "❌ Formato de dirección de billetera {currency_name} inválido. Por favor verifica y envíala de nuevo.",
        "wallet_saved": "✅ Tu billetera de {currency_name} ha sido guardada:\n<code>{address}</code>\n\n¡Ahora estás listo para jugar!",
        "current_wallet": "👛 Tu billetera de {currency_name} actual:\n<code>{address}</code>\n\nPara cambiarla, envía una nueva dirección de billetera.",
        "no_wallet_set": "Aún no has configurado una billetera de {currency_name}. Por favor, configura una para recibir premios.",

        "main_menu_text": "🍀 <b>Menú Principal</b>\n\n🏦 <b>Banco Actual:</b> ${bank:.2f}\n🎟️ <b>Tus Boletos:</b> {tickets}\n\nElige una opción:",
        "buy_ticket_button": "🎟 Comprar Boletos",
        "my_wallet_button": "👛 Mi Billetera",
        "language_button": "🌐 Idioma",
        "channel_button": "📢 Anuncios",
        "back_to_menu": "🔙 Volver al Menú",

        "choose_payment_currency": "💸 Elige una moneda para pagar:",
        "payment_creation_text": (
            "Para comprar <b>{tickets} boleto(s)</b>, envía <b>{amount} {currency}</b>\n\n"
            "A la dirección: <code>{address}</code>\n\n"
            "<i>Este pago es válido por 10 minutos. Después de la confirmación, tus boletos serán acreditados automáticamente.</i>"
        ),
        "payment_failed": "❌ Error al crear el pago. Inténtalo de nuevo en unos minutos.",
        "payment_received_notification": "✅ ¡Pago recibido! <b>{tickets} boleto(s)</b> han sido añadidos a tu cuenta. ¡Buena suerte!",

        "winner_dm": "🎉 ¡Felicidades! ¡Has ganado <b>${prize:.2f}</b> en la lotería semanal!\n\nTu premio está siendo procesado y será enviado a tu billetera: <code>{wallet}</code>",
        "winner_dm_no_wallet": "🎉 ¡Felicidades! ¡Has ganado <b>${prize:.2f}</b>!\n\nPor favor configura tu billetera de pago usando el menú. Un administrador te contactará pronto.",

        "admin_payout_notification": (
            "‼️ <b>PAGO MANUAL REQUERIDO</b> ‼️\n\n"
            "¡Ganador seleccionado!\n\n"
            "<b>Usuario:</b> {user_mention} (ID: <code>{user_id}</code>)\n"
            "<b>Premio:</b> ${prize:.2f}\n"
            "<b>Moneda:</b> {currency_name}\n"
            "<b>Billetera:</b> <code>{wallet_address}</code>\n\n"
            "Por favor envía el premio a esta dirección."
        ),
        "draw_announcement_channel": (
            "🏆 <b>¡Sorteo Semanal Completo!</b> 🏆\n\n"
            "¡Premio de <b>${prize:.2f}</b> va para el usuario <code>...{user_id_part}</code>!\n\n"
            "🎉 ¡Felicidades! 🎉\n\n"
            "<b>Total Recaudado:</b> ${total_collected:.2f}\n"
            "<b>Hash Provablemente Justo:</b> <code>{btc_hash}</code>\n\n"
            "¡Nueva ronda ha comenzado. Buena suerte a todos!"
        ),
        "rollover_announcement_channel": (
            "⚠️ <b>¡Sorteo Pospuesto!</b> ⚠️\n\n"
            "El banco no alcanzó el mínimo de ${min_bank:.2f}.\n"
            "Los ${bank:.2f} recaudados y todos los boletos se transfieren a la próxima semana.\n\n"
            "¡Sigue participando! 🍀"
        ),
    },

    "pt": {
        "welcome_photo": "👋 Bem-vindo ao CryptoLuck! Uma nova chance de ganhar toda semana.\n\nPor favor, escolha seu idioma para continuar.",
        "choose_language": "🌐 Escolha seu idioma:",
        "language_set": "✅ Idioma alterado para Português.",

        "wallet_setup_prompt": "Primeiro, vamos configurar sua carteira de pagamento para <b>{currency_name}</b>. É aqui que você receberá seu prêmio se ganhar.\n\nPor favor, envie o endereço da sua carteira {currency_name}.",
        "invalid_wallet_address": "❌ Formato de endereço de carteira {currency_name} inválido. Verifique e envie novamente.",
        "wallet_saved": "✅ Sua carteira {currency_name} foi salva:\n<code>{address}</code>\n\nAgora você está pronto para jogar!",
        "current_wallet": "👛 Sua carteira {currency_name} atual:\n<code>{address}</code>\n\nPara alterá-la, envie um novo endereço de carteira.",
        "no_wallet_set": "Você ainda não configurou uma carteira {currency_name}. Por favor, configure uma para receber prêmios.",

        "main_menu_text": "🍀 <b>Menu Principal</b>\n\n🏦 <b>Banco Atual:</b> ${bank:.2f}\n🎟️ <b>Seus Bilhetes:</b> {tickets}\n\nEscolha uma opção:",
        "buy_ticket_button": "🎟 Comprar Bilhetes",
        "my_wallet_button": "👛 Minha Carteira",
        "language_button": "🌐 Idioma",
        "channel_button": "📢 Anúncios",
        "back_to_menu": "🔙 Voltar ao Menu",

        "choose_payment_currency": "💸 Escolha uma moeda para pagar:",
        "payment_creation_text": (
            "Para comprar <b>{tickets} bilhete(s)</b>, envie <b>{amount} {currency}</b>\n\n"
            "Para o endereço: <code>{address}</code>\n\n"
            "<i>Este pagamento é válido por 10 minutos. Após a confirmação, seus bilhetes serão creditados automaticamente.</i>"
        ),
        "payment_failed": "❌ Falha ao criar o pagamento. Tente novamente em alguns minutos.",
        "payment_received_notification": "✅ Pagamento recebido! <b>{tickets} bilhete(s)</b> foram adicionados à sua conta. Boa sorte!",

        "winner_dm": "🎉 Parabéns! Você ganhou <b>${prize:.2f}</b> na loteria semanal!\n\nSeu prêmio está sendo processado e será enviado para sua carteira: <code>{wallet}</code>",
        "winner_dm_no_wallet": "🎉 Parabéns! Você ganhou <b>${prize:.2f}</b>!\n\nPor favor, configure sua carteira de pagamento usando o menu. Um administrador entrará em contato em breve.",

        "draw_announcement_channel": (
            "🏆 <b>Sorteio Semanal Concluído!</b> 🏆\n\n"
            "Prêmio de <b>${prize:.2f}</b> vai para o usuário <code>...{user_id_part}</code>!\n\n"
            "🎉 Parabéns! 🎉\n\n"
            "<b>Total Arrecadado:</b> ${total_collected:.2f}\n"
            "<b>Hash Comprovadamente Justo:</b> <code>{btc_hash}</code>\n\n"
            "Nova rodada começou. Boa sorte a todos!"
        ),
        "rollover_announcement_channel": (
            "⚠️ <b>Sorteio Adiado!</b> ⚠️\n\n"
            "O banco não atingiu o mínimo de ${min_bank:.2f}.\n"
            "Os ${bank:.2f} arrecadados e todos os bilhetes passam para a próxima semana.\n\n"
            "Continue participando! 🍀"
        ),
    },

    "fr": {
        "welcome_photo": "👋 Bienvenue sur CryptoLuck! Une nouvelle chance de gagner chaque semaine.\n\nVeuillez choisir votre langue pour continuer.",
        "choose_language": "🌐 Choisissez votre langue:",
        "language_set": "✅ Langue changée en Français.",

        "wallet_setup_prompt": "Tout d'abord, configurons votre portefeuille de paiement pour <b>{currency_name}</b>. C'est là que vous recevrez votre prix si vous gagnez.\n\nVeuillez envoyer l'adresse de votre portefeuille {currency_name}.",
        "invalid_wallet_address": "❌ Format d'adresse de portefeuille {currency_name} invalide. Veuillez vérifier et la renvoyer.",
        "wallet_saved": "✅ Votre portefeuille {currency_name} a été enregistré:\n<code>{address}</code>\n\nMaintenant, vous êtes prêt à jouer!",
        "current_wallet": "👛 Votre portefeuille {currency_name} actuel:\n<code>{address}</code>\n\nPour le changer, envoyez une nouvelle adresse de portefeuille.",
        "no_wallet_set": "Vous n'avez pas encore configuré de portefeuille {currency_name}. Veuillez en configurer un pour recevoir des prix.",

        "main_menu_text": "🍀 <b>Menu Principal</b>\n\n🏦 <b>Banque Actuelle:</b> ${bank:.2f}\n🎟️ <b>Vos Billets:</b> {tickets}\n\nChoisissez une option:",
        "buy_ticket_button": "🎟 Acheter des Billets",
        "my_wallet_button": "👛 Mon Portefeuille",
        "language_button": "🌐 Langue",
        "channel_button": "📢 Annonces",
        "back_to_menu": "🔙 Retour au Menu",

        "choose_payment_currency": "💸 Choisissez une devise pour payer:",
        "payment_creation_text": (
            "Pour acheter <b>{tickets} billet(s)</b>, veuillez envoyer <b>{amount} {currency}</b>\n\n"
            "À l'adresse: <code>{address}</code>\n\n"
            "<i>Ce paiement est valable 10 minutes. Après confirmation, vos billets seront automatiquement crédités.</i>"
        ),
        "payment_failed": "❌ Échec de création du paiement. Veuillez réessayer dans quelques minutes.",
        "payment_received_notification": "✅ Paiement reçu! <b>{tickets} billet(s)</b> ont été ajoutés à votre compte. Bonne chance!",

        "winner_dm": "🎉 Félicitations! Vous avez gagné <b>${prize:.2f}</b> à la loterie hebdomadaire!\n\nVotre prix est en cours de traitement et sera envoyé à votre portefeuille: <code>{wallet}</code>",
        "winner_dm_no_wallet": "🎉 Félicitations! Vous avez gagné <b>${prize:.2f}</b>!\n\nVeuillez configurer votre portefeuille de paiement en utilisant le menu. Un administrateur vous contactera sous peu.",

        "draw_announcement_channel": (
            "🏆 <b>Tirage Hebdomadaire Terminé!</b> 🏆\n\n"
            "Le prix de <b>${prize:.2f}</b> va à l'utilisateur <code>...{user_id_part}</code>!\n\n"
            "🎉 Félicitations! 🎉\n\n"
            "<b>Total Collecté:</b> ${total_collected:.2f}\n"
            "<b>Hash Prouvablement Équitable:</b> <code>{btc_hash}</code>\n\n"
            "Une nouvelle rodada a commencé. Bonne chance à tous!"
        ),
        "rollover_announcement_channel": (
            "⚠️ <b>Tirage Reporté!</b> ⚠️\n\n"
            "La banque n'a pas atteint le minimum de ${min_bank:.2f}.\n"
            "Les ${bank:.2f} collectés et tous les billets sont reportés à la semaine prochaine.\n\n"
            "Continuez à participer! 🍀"
        ),
    }
}