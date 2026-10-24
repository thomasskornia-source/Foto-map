import unittest
from server import asset_url, coordinates, iso_date, token_from_url

class AlbumTests(unittest.TestCase):
    def test_current_public_link(self):
        self.assertEqual(token_from_url("https://photos.icloud.com/shared/album/abcDEF_123456"),"abcDEF_123456")
    def test_rejects_other_hosts(self):
        with self.assertRaises(ValueError): token_from_url("https://example.com/shared/album/abcDEF_123456")
    def test_rejects_empty_token(self):
        with self.assertRaises(ValueError): token_from_url("https://photos.icloud.com/shared/album/")
    def test_coordinates_validate_bounds(self):
        self.assertEqual(coordinates({"latitude":{"value":43.4},"longitude":{"value":10.86}}),(43.4,10.86))
        self.assertEqual(coordinates({"latitude":{"value":120},"longitude":{"value":10}}),(None,None))
    def test_millisecond_date(self):
        self.assertEqual(iso_date(1700000000000),"2023-11-14T22:13:20Z")
    def test_asset_urls_are_apple_hosts_only(self):
        self.assertTrue(asset_url({"resOriginalRes":{"value":{"downloadURL":"https://cvws.icloud-content.com/photo"}}}))
        self.assertIsNone(asset_url({"resOriginalRes":{"value":{"downloadURL":"https://example.com/photo"}}}))

if __name__=="__main__": unittest.main()
