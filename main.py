"""Used for getting the user's PASSWORD_STORE_DIR env var"""
from os import getenv, system
from pathlib import Path
import qrcode
import re
import subprocess
from gi.repository import Notify, GdkPixbuf
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction

# from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

prefix = ""

# NOTE: The program 'qrencode' or some python module will be required to generate QR codes


def sort_by_basename(fname):
    """Takes Path objects, and returns their name so they may be sorted by list()"""
    return fname.name


class PassExtension(Extension):
    """Initializes the extension"""

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    """Runs when the text in the prompt is changed"""

    def on_event(self, event, extension):
        keyword = event.get_keyword()
        search_str = event.get_argument()
        if search_str:
            password_files = sorted(
                list(prefix.rglob(f"*{search_str}*.gpg")), key=sort_by_basename
            )
        else:
            password_files = sorted(list(prefix.rglob("*.gpg")), key=sort_by_basename)

        items = []
        show_pattern = re.compile(extension.preferences["show_regex"])
        for pfile in password_files:
            if re.search(show_pattern, pfile.stem):
                items.append(
                    ExtensionResultItem(
                        icon="images/application-pgp-encrypted-alt.svg",
                        name=f"{pfile.stem}",
                        description=f"{pfile}".replace(str(Path.home()), "~"),
                        on_enter=ExtensionCustomAction(
                            {"keyword": keyword, "password_file": pfile}
                        ),
                    )
                )
            if len(items) >= int(extension.preferences["max_display_lines"]):
                break

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    """Runs when the user submits an item"""

    def on_event(self, event, extension):
        keyword = event.get_data()["keyword"]
        pass_arg = str(event.get_data()["password_file"].relative_to(prefix)).replace(
            ".gpg", ""
        )
        if keyword == extension.preferences["keyword-otp"]:
            pass_cmd = f"pass otp -c {pass_arg} > /dev/null".format(pass_arg)
            system(pass_cmd)
            if extension.preferences["show_notification"] == "yes":
                Notify.Notification.new(
                    f"Copied {pass_arg} to clipboard.",
                    "Will clear in 45 seconds.",
                    "object-unlocked",
                ).show()
        elif keyword == extension.preferences["keyword-otp-qr"]:
            pass_name = event.get_data()["password_file"].stem
            token = subprocess.check_output(["pass", "show", pass_arg])
            qrcode.make(token).show()
        else:
            raise RuntimeError(f"An invalid keyword, '{keyword}', was passed")


if __name__ == "__main__":
    prefix = Path(getenv("PASSWORD_STORE_DIR", "~/.password-store")).expanduser()
    Notify.init("Pass OTP for Ulauncher")
    PassExtension().run()
    Notify.uninit()
