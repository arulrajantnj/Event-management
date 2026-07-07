import os

PROMPT_FILE = os.path.join(
    "static",
    "ai",
    "prompt.txt"
)


DEFAULT_PROMPT = """
Create a realistic award ceremony photograph.

The uploaded person is a teacher.

Use the teacher as the main subject.

The teacher is standing on a decorated stage.

The teacher is smiling while receiving a certificate.

The ceremony is formal and professional.

The background is a government educational function.

Realistic lighting.

Natural shadows.

Professional DSLR photography.

Ultra realistic.

High quality.

4K.

"""


def load_prompt():

    if os.path.exists(PROMPT_FILE):

        with open(
            PROMPT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()

    return DEFAULT_PROMPT


def build_prompt(participant):

    prompt = load_prompt()

    prompt += f"""

Teacher Name : {participant.teacher_name}

Designation : {participant.designation}

School : {participant.school_name}

Block : {participant.block}

The teacher should appear naturally in the ceremony.

Maintain the uploaded teacher's facial identity.

"""

    return prompt