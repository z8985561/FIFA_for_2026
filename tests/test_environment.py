def test_importable_package() -> None:
    import src

    assert src is not None
