import os
import unittest
from unittest.mock import patch, MagicMock
from downloader import download_audio, download_video, COOKIES_FILE_PATH

class TestDownloader(unittest.TestCase):

    @patch('downloader.YoutubeDL')
    def test_download_audio_with_cookies(self, mock_yt):
        # Simulate cookies file exists
        with patch('os.path.exists', return_value=True):
            mock_instance = mock_yt.return_value.__enter__.return_value
            mock_instance.extract_info.return_value = {'title': 'test_audio'}
            mock_instance.prepare_filename.return_value = 'test_audio.mp3'

            filename, title, elapsed = download_audio('http://fakeurl.com')
            self.assertEqual(title, 'test_audio')
            self.assertTrue(filename.endswith('.mp3'))
            mock_instance.extract_info.assert_called_once()

    @patch('downloader.YoutubeDL')
    def test_download_audio_without_cookies(self, mock_yt):
        # Simulate cookies file does not exist
        with patch('os.path.exists', return_value=False):
            mock_instance = mock_yt.return_value.__enter__.return_value
            mock_instance.extract_info.return_value = {'title': 'test_audio'}
            mock_instance.prepare_filename.return_value = 'test_audio.mp3'

            filename, title, elapsed = download_audio('http://fakeurl.com')
            self.assertEqual(title, 'test_audio')
            self.assertTrue(filename.endswith('.mp3'))
            mock_instance.extract_info.assert_called_once()

    @patch('downloader.YoutubeDL')
    def test_download_video_with_cookies(self, mock_yt):
        with patch('os.path.exists', return_value=True):
            mock_instance = mock_yt.return_value.__enter__.return_value
            mock_instance.extract_info.return_value = {'title': 'test_video'}
            mock_instance.prepare_filename.return_value = 'test_video.mp4'

            filename, title, elapsed = download_video('http://fakeurl.com')
            self.assertEqual(title, 'test_video')
            self.assertTrue(filename.endswith('.mp4'))
            mock_instance.extract_info.assert_called_once()

    @patch('downloader.YoutubeDL')
    def test_download_video_without_cookies(self, mock_yt):
        with patch('os.path.exists', return_value=False):
            mock_instance = mock_yt.return_value.__enter__.return_value
            mock_instance.extract_info.return_value = {'title': 'test_video'}
            mock_instance.prepare_filename.return_value = 'test_video.mp4'

            filename, title, elapsed = download_video('http://fakeurl.com')
            self.assertEqual(title, 'test_video')
            self.assertTrue(filename.endswith('.mp4'))
            mock_instance.extract_info.assert_called_once()

if __name__ == '__main__':
    unittest.main()
