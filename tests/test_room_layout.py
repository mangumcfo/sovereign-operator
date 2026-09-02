from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "web" / "public" / "index.html").read_text()


def test_room_menu_is_a_left_rail_without_changing_panels():
    assert 'class="shell"' in HTML
    assert '<nav id="nav" aria-label="Room menu"></nav>' in HTML
    assert "grid-template-columns:180px minmax(0,1fr)" in HTML
    assert "flex-direction:column" in HTML
    assert '["needs","Needs You"]' in HTML
    assert '["port","Port draft"]' in HTML


def test_room_menu_collapses_for_small_screens():
    assert "@media(max-width:700px)" in HTML
    assert "nav{position:static;flex-direction:row" in HTML
