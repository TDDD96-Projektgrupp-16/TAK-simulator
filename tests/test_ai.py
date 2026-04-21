from tak_simulator.local_ai.py import Client_AI, Role

def test_generate_conversation():
    ai = Client_AI("Bernard", Role.TEAM_MEMBER)

    response = ai.respond("Michael", "I want Ice Cream")

    assert response is not None

    print(response)


test_generate_conversation()
    
