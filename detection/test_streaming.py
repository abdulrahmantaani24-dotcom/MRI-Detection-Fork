"""Interrupted bounded-stream tests, artificial bytes only."""
import unittest
import json
import urllib.error
from unittest.mock import patch
from detection.test_acquisition import AcquisitionSafety as _Fixture, Response
from detection import acquisition as a


class ReadResponse(Response):
    def __init__(self, body, **kwargs):
        super().__init__(body, **kwargs)
        self.read_sizes = []
        self.fail = False

    def read1(self, n):
        self.read_sizes.append(n)
        if self.fail:
            raise TimeoutError('synthetic read timeout')
        chunk = super().read(min(n, 5))
        self.fail = bool(chunk)
        return chunk


# Reuse only fixture setup, not inherited test methods.
class StreamingTests(unittest.TestCase):
    setUp = _Fixture.setUp
    def test_interruption_then_verified_range_retry(self):
        first = ReadResponse(self.payload)
        second = Response(self.payload[5:], 206, {'Content-Range': f'bytes 5-{len(self.payload)-1}/{len(self.payload)}', 'ETag': '"v1"'})
        with patch.object(a, '_request', side_effect=[first, second]) as request, patch.object(a.time, 'sleep'), patch.object(a.os, 'fsync', wraps=a.os.fsync) as sync:
            result = a.download_verified(self.asset, self.root, max_bytes=100, chunk_bytes=8)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(request.call_args.kwargs['headers']['Range'], 'bytes=5-')
        self.assertEqual(first.read_sizes, [8, 8])
        self.assertTrue(sync.called)
        status = json.loads((self.root / 'test.bin.download_status.json').read_text())
        self.assertEqual(status['bytes_saved'], len(self.payload))
        self.assertEqual(status['attempt'], 2)

    def test_orphan_metadata_without_bytes_is_fresh_not_complete(self):
        a.atomic_json(self.root / 'test.bin.resume.json', {'validator': None, 'total': len(self.payload)})
        with patch.object(a, '_request', return_value=Response(self.payload)) as request:
            a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual(request.call_args.kwargs['headers'], {})
        self.assertEqual((self.root / 'test.bin').read_bytes(), self.payload)

    def test_missing_validator_preserves_actual_partial(self):
        (self.root / 'test.bin.part').write_bytes(b'bytes')
        a.atomic_json(self.root / 'test.bin.resume.json', {'url': self.asset['url'], 'validator': None})
        with patch.object(a, '_request') as request:
            with self.assertRaisesRegex(RuntimeError, 'no trusted resume validator'):
                a.download_verified(self.asset, self.root, max_bytes=100)
        request.assert_not_called()
        self.assertEqual((self.root / 'test.bin.part').read_bytes(), b'bytes')

    def test_server_failures_are_bounded_and_timeouts_passed(self):
        error = urllib.error.HTTPError(self.asset['url'], 503, 'unavailable', {}, None)
        with patch.object(a, '_request', side_effect=error) as request, patch.object(a.time, 'sleep'):
            with self.assertRaises(urllib.error.HTTPError):
                a.download_verified(self.asset, self.root, max_bytes=100, connect_timeout=12, read_timeout=23)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args.kwargs['connect_timeout'], 12)
        self.assertEqual(request.call_args.kwargs['read_timeout'], 23)
        status = json.loads((self.root / 'test.bin.download_status.json').read_text())
        self.assertEqual(status['status'], 'interrupted')
        self.assertEqual(status['bytes_saved'], 0)

    def test_interruption_without_validator_keeps_durable_bytes_and_reports_gap(self):
        response = ReadResponse(self.payload, headers={'Content-Length': str(len(self.payload))})
        with patch.object(a, '_request', return_value=response) as request:
            with self.assertRaises(TimeoutError):
                a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual(request.call_count, 1)
        self.assertEqual((self.root / 'test.bin.part').read_bytes(), self.payload[:5])
        status = json.loads((self.root / 'test.bin.download_status.json').read_text())
        self.assertEqual(status['status'], 'resume_unavailable')
        self.assertEqual(status['bytes_saved'], 5)

    def test_partial_symlink_is_rejected_before_write(self):
        original = self.root / 'original'
        original.write_bytes(b'preserve')
        (self.root / 'test.bin.part').symlink_to(original)
        with patch.object(a, '_request') as request:
            with self.assertRaisesRegex(ValueError, 'symlink'):
                a.download_verified(self.asset, self.root, max_bytes=100)
        request.assert_not_called()
        self.assertEqual(original.read_bytes(), b'preserve')

    def test_no_retry_for_permanent_server_error(self):
        with patch.object(a, '_request', side_effect=urllib.error.HTTPError(self.asset['url'], 403, 'denied', {}, None)) as request:
            with self.assertRaises(urllib.error.HTTPError):
                a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual(request.call_count, 1)

    def test_wrong_range_end_does_not_append(self):
        (self.root / 'test.bin.part').write_bytes(b'abc')
        a.atomic_json(self.root / 'test.bin.resume.json', {'url': self.asset['url'], 'validator': '"v1"'})
        with patch.object(a, '_request', return_value=Response(b'xyz', 206, {'Content-Range': 'bytes 3-5/99'})):
            with self.assertRaisesRegex(RuntimeError, 'Content-Range end'):
                a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual((self.root / 'test.bin.part').read_bytes(), b'abc')

# Do not expose the imported fixture TestCase to unittest discovery.
del _Fixture
