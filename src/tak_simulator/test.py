from tak_simulator.scenario import ATAKTakv, EmulatorOptions, EmulatorOptionsBase
from tak_simulator.xml_parse import (
    ChatDetail,
    build_chat_detail_for_direct_message,
    decode_chat_detail,
    encode_chat_detail,
)


class Foo:
    pass


options = Foo()
options.like = "atak"
options.uid = "ANDROID-dbdc90afc2ca1328"
options.callsign = "tak-emulator"
options.type = "a-f-G-U-C"
options.path = []

x = build_chat_detail_for_direct_message(
    options,
    recipient_id="algal",
    recipient_callsign="Algot Johansson",
    endpoint="10.225.252.189:4242",
    message="hdj",
)

b = encode_chat_detail(x)

print(b)
