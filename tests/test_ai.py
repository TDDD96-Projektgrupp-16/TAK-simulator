from tak_simulator.local_ai import LocalAiUser, generate_conversation


def test_generate_conversation():
    result = generate_conversation(
        [
            LocalAiUser("Bert", "A cool dude that likes to do backflips"),
            LocalAiUser("Adam", "A dude that hates backflips"),
        ]
    )
    assert result is not None
    print(result)
