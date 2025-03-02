from pytigon.pytigon_run import run


def test_gen_doc():
    result = run(
        [
            "",
            "run__schtest.test_spreadsheet",
        ]
    )
    assert result is True


if __name__ == "__main__":
    test_gen_doc()
