import unittest
from server import asset, coords, token_from_url

class AlbumTests(unittest.TestCase):
 def test_current_shared_album_link(self):
  self.assertEqual(token_from_url("https://photos.icloud.com/shared/album/abcDEF_123456"),"abcDEF_123456")
 def test_rejects_other_host(self):
  with self.assertRaises(ValueError):token_from_url("https://example.com/shared/album/abcDEF_123456")
 def test_rejects_missing_key(self):
  with self.assertRaises(ValueError):token_from_url("https://photos.icloud.com/shared/album/")
 def test_coordinate_bounds(self):
  self.assertEqual(coords({"latitude":{"value":43.4},"longitude":{"value":10.86}}),(43.4,10.86))
  self.assertEqual(coords({"latitude":{"value":120},"longitude":{"value":10}}),(None,None))
 def test_only_apple_asset_urls(self):
  self.assertEqual(asset({"resOriginalRes":{"value":{"downloadURL":"https://cvws.icloud-content.com/photo"}}}),"https://cvws.icloud-content.com/photo")
  self.assertIsNone(asset({"resOriginalRes":{"value":{"downloadURL":"https://example.com/photo"}}}))
if __name__=="__main__":unittest.main()
