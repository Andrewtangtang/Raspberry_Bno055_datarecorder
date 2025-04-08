from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

class GoogleDriveUploader:
    """Class for uploading files to Google Drive using service account."""
    
    def __init__(self, service_account_file='heroic-idea-430007-m2-ea9afcaa98f9.json', 
                 folder_id='1Ty2lTwjSDpZOyte5wE05lx5BGpOk1fY9'):
        """Initialize the uploader with service account credentials.
        
        Args:
            service_account_file: Path to the service account JSON file
            folder_id: Default Google Drive folder ID to upload files to
        """
        self.service_account_file = service_account_file
        self.folder_id = folder_id
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.service = None
        
        # Initialize the service
        self._initialize_service()
    
    def _initialize_service(self):
        """Create and initialize the Google Drive service."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes)
            self.service = build('drive', 'v3', credentials=credentials)
            return True
        except Exception as e:
            print(f'Error initializing Drive service: {e}')
            self.service = None
            return False
    
    def upload_file(self, file_path, folder_id=None):
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the local file to upload
            folder_id: ID of the Google Drive folder to upload to (optional)
                      If not provided, uses the default folder_id from initialization
        
        Returns:
            File ID if successful, None if failed
        """
        if not os.path.exists(file_path):
            print(f'Error: File {file_path} does not exist')
            return None

        if not self.service:
            success = self._initialize_service()
            if not success:
                return None

        target_folder = folder_id or self.folder_id

        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [target_folder] if target_folder else None
            }

            # Determine MIME type based on file extension
            mime_type = 'text/csv' if file_path.endswith('.csv') else 'application/octet-stream'
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')
            print(f'Successfully uploaded {file_path}')
            print(f'File ID: {file_id}')
            return file_id

        except Exception as e:
            print(f'Error uploading file: {e}')
            return None


def test_uploader():
    """Test the GoogleDriveUploader class."""
    # Create a test CSV file
    test_file = 'test_upload.csv'
    try:
        with open(test_file, 'w') as f:
            f.write('test1,test2,test3\n1,2,3\n')
        
        # Create uploader instance
        uploader = GoogleDriveUploader()
        
        # Upload the test file
        file_id = uploader.upload_file(test_file)
        if file_id:
            print('Test successful!')
        
    except Exception as e:
        print(f'Test failed: {e}')
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == '__main__':
    test_uploader()
