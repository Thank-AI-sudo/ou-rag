
import re


def validate_citations(
    answer: str,
    sources: list[dict]
) -> tuple[str, list[dict]]:
    """
    Kiểm tra citation và chỉ giữ các sources
    được trích dẫn trong answer.
    """

    valid_numbers = {
        source["number"]
        for source in sources
    }

    def replace_citation(match):
        number = int(match.group(1))

        if number in valid_numbers:
            return match.group(0)

        return ""

    cleaned_answer = re.sub(
        r"\[(\d+)\]",
        replace_citation,
        answer
    )

    used_numbers = {
        int(number)
        for number in re.findall(
            r"\[(\d+)\]",
            cleaned_answer
        )
    }

    used_sources = [
        source
        for source in sources
        if source["number"] in used_numbers
    ]

    return cleaned_answer, used_sources
