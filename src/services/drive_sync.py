"""
Google Drive Sync Service
Downloads audio files from Google Drive, organizes by date
"""

import os
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ['https://www.googleapis.com/auth/drive']


class DriveSync:
    """Sync audio files from Google Drive"""

    def __init__(self, credentials_path: str, token_path: str, folder_id: str):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.folder_id = folder_id
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        creds = None

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('drive', 'v3', credentials=creds)
        return True

    def list_audio_files(self) -> List[Dict[str, Any]]:
        """List all audio files in the Drive folder"""
        if not self.service:
            raise Exception("Not authenticated")

        query = f"'{self.folder_id}' in parents and trashed=false and (mimeType contains 'audio/' or name contains '.mp3' or name contains '.wav' or name contains '.m4a' or name contains '.aac')"

        results = self.service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, createdTime, modifiedTime, size, mimeType)"
        ).execute()

        return results.get('files', [])

    def download_file(self, file_id: str, destination_path: str) -> bool:
        """Download a file from Google Drive"""
        if not self.service:
            raise Exception("Not authenticated")

        try:
            Path(destination_path).parent.mkdir(parents=True, exist_ok=True)

            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            with open(destination_path, 'wb') as f:
                f.write(fh.getvalue())

            return True

        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        if not self.service:
            raise Exception("Not authenticated")

        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Delete failed: {e}")
            return False

    def organize_by_date(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize files by date from Drive metadata (createdTime)

        Returns:
            Dict mapping date string (YYYY-MM-DD) to list of files
        """
        files_by_date = defaultdict(list)

        for file in files:
            # Use createdTime from Drive metadata
            created_time = file.get('createdTime')
            if created_time:
                # Parse ISO 8601: 2024-01-26T10:30:00.000Z
                date_str = created_time[:10]  # Extract YYYY-MM-DD
            else:
                # Fallback to today
                date_str = datetime.now().strftime('%Y-%m-%d')

            files_by_date[date_str].append(file)

        return dict(files_by_date)
