from datetime import datetime, timedelta
import os
from typing import Union

from aiogram.types import FSInputFile, InlineKeyboardMarkup, CallbackQuery, Message

from tgbot.mongo_db.db_api import files, subs, trial
from tgbot.utils.get_image import get_next_image_filename
from tgbot.phrasebook.lexicon_ru import LEXICON_RU


async def process_successful_re_subscription_payment(
    call: CallbackQuery,
    end_date_str: str,
    support_keyboard: InlineKeyboardMarkup,
    settings_keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Processes a successful re-subscription payment.

    Args:
        call (CallbackQuery): The incoming callback query.
        end_date_str (str): The end date of the subscription.
        support_keyboard (InlineKeyboardMarkup): The support keyboard.
        settings_keyboard (InlineKeyboardMarkup): The settings keyboard.

    Returns:
        None
    """
    user_id = call.from_user.id
    date = datetime.now()
    user_data = await files.find_one({"user_id": user_id})

    sub_flag = (
        await subs.find_one(filter={"user_id": user_id, "end_date": {"$gt": date}})
    ).get("client_id", "")

    if len(sub_flag) > 10:
        image_filename = ""
        client_id = ""
        pk = ""

        async for image in get_next_image_filename():
            image_filename = image
            break

        try:
            pk = image_filename.split("/")[3].split(".")[0]
            client_id = "Client_№" + pk
        except Exception as e:
            print(e)
        if not os.path.exists(image_filename):
            await call.message.answer(
                text=LEXICON_RU["empty_qr"], reply_markup=support_keyboard
            )

        image_from_pc = FSInputFile(image_filename)

        result = await call.message.answer_photo(
            photo=image_from_pc,
            caption=f"✅  Оплата прошла успешно!!! \n"
            f"🤝 Ваш QR - код для подключения ⤴️ \n\n"
            f"Cрок действия подписки: до {end_date_str}\n\n"
            f"Меню настроек для подключения ⤵️ ",
            reply_markup=settings_keyboard,
        )
        await files.update_one(
            filter={"user_id": user_id},
            update={"$set": {"photo_id": result.photo[-1].file_id, "pk": pk}},
        )
        await subs.update_one(
            filter={"user_id": user_id, "end_date": {"$gt": date}},
            update={"$set": {"client_id": client_id}},
        )
        os.remove(image_filename)
    else:
        photo_id = user_data.get("photo_id")
        if photo_id:
            await call.message.answer_photo(
                photo=photo_id,
                caption=f"✅  Оплата прошла успешно!!! \n"
                f"Спасибо что Вы снова с нами! 🤝\n"
                f" Ваш QR - код для подключения ⤴️ \n\n"
                f"Общий срок действия подписки: до {end_date_str}\n\n"
                f"Меню настроек для подключения ⤵️ ",
                reply_markup=settings_keyboard,
            )
        else:
            await call.message.answer(
                text=f"✅  Оплата прошла успешно!!! \n"
                f"Спасибо что Вы снова с нами! 🤝\n\n\n"
                f"Общий срок действия подписки: до {end_date_str}\n\n",
                reply_markup=support_keyboard,
            )


async def process_successful_first_subscription_payment(
    call: CallbackQuery,
    end_date_str: str,
    support_keyboard: InlineKeyboardMarkup,
    settings_keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Processes a successful first subscription payment.

    Args:
        call (CallbackQuery): The incoming callback query..
        end_date_str (str): The end date of the subscription.
        support_keyboard (InlineKeyboardMarkup): The support keyboard.
        settings_keyboard (InlineKeyboardMarkup): The settings keyboard.

    Returns:
        None
    """
    user_id = call.from_user.id
    date: datetime = datetime.now()

    image_filename = ""
    client_id = ""
    pk = ""

    async for image in get_next_image_filename():
        image_filename = image
        break
    try:
        pk = image_filename.split("/")[3].split(".")[0]
        client_id = "Client_№" + pk
    except Exception as e:
        print(e)
    if not os.path.exists(image_filename):
        await call.message.answer(
            text=LEXICON_RU["empty_qr"],
            reply_markup=support_keyboard,
        )

    image_from_pc = FSInputFile(image_filename)

    result = await call.message.answer_photo(
        photo=image_from_pc,
        caption=f"✅  Оплата прошла успешно!!! \n\n\n"
        f"Ваш QR - код для подключения ⤴️ \n\n"
        f"<b>Срок действия:</b> до {end_date_str}\n\n"
        f"Перейдите в меню настроек для подключения",
        reply_markup=settings_keyboard,
    )

    await files.insert_one(
        {"user_id": user_id, "photo_id": result.photo[-1].file_id, "pk": pk}
    )
    await subs.update_one(
        filter={"user_id": user_id, "end_date": {"$gt": date}},
        update={"$set": {"client_id": client_id}},
    )
    os.remove(image_filename)


async def process_trial_subscription(
    query: Union[Message, CallbackQuery],
    settings_keyboard: InlineKeyboardMarkup,
    client_id: str,
    image_filename: str,
    pk: str,
) -> None:
    """
    Processes a trial subscription.

    Args:
        query (Union[Message, CallbackQuery]): The query object representing the message.
        settings_keyboard (InlineKeyboardMarkup): The settings keyboard.
        client_id (str): The client ID.
        image_filename (str): The image filename.
        pk (str): The package ID.

    Returns:
        None
    """
    user_id: int = query.from_user.id
    date: datetime = datetime.now()

    await subs.delete_many(filter={"user_id": user_id})

    end_date = date + timedelta(days=3)

    await trial.insert_one(
        {
            "user_id": user_id,
            "trial_flag": "on",
            "start_date": date,
            "end_date": end_date,
        }
    )

    await subs.insert_one(
        document={
            "user_id": user_id,
            "start_date": date,
            "end_date": end_date,
            "client_id": client_id,
        }
    )

    image_from_pc = FSInputFile(image_filename)

    end_date_str: str = end_date.strftime("%d.%m.%Y")

    result = await query.answer_photo(
        photo=image_from_pc,
        caption=f"✅  Подписка успешно оформлена!!! \n\n\n"
        f"Ваш QR - код для подключения ⤴️ \n\n"
        f"<b>Срок действия пробного периода:</b> до {end_date_str}\n\n"
        f"Перейдите в меню настроек для подключения",
        reply_markup=settings_keyboard,
    )

    await files.insert_one(
        {"user_id": user_id, "photo_id": result.photo[-1].file_id, "pk": pk}
    )

    os.remove(image_filename)
