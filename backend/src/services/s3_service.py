"""AWS S3 service for video storage"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional
import logging
from datetime import timedelta

from src.config import Settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for interacting with AWS S3"""
    
    def __init__(self, settings: Settings):
        """Initialize S3 service with configuration
        
        Args:
            settings: Application settings containing AWS credentials
        """
        self.settings = settings
        self.bucket_name = settings.s3_bucket_name
        
        # Configure boto3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3, 'mode': 'adaptive'}
            )
        )
        
        logger.info(f"S3Service initialized for bucket: {self.bucket_name}")
    
    def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str,
        expiration: Optional[int] = None
    ) -> dict:
        """Generate a pre-signed URL for uploading a file to S3
        
        Args:
            object_key: The S3 object key (path) for the file
            content_type: MIME type of the file
            expiration: URL expiration time in seconds (default from settings)
            
        Returns:
            Dictionary containing the pre-signed URL and fields
            
        Raises:
            ClientError: If URL generation fails
        """
        if expiration is None:
            expiration = self.settings.s3_presigned_url_expiration
        
        try:
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=object_key,
                Fields={'Content-Type': content_type},
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, self.settings.max_upload_size_mb * 1024 * 1024]
                ],
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned upload URL for: {object_key}")
            return presigned_post
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def generate_presigned_download_url(
        self,
        object_key: str,
        expiration: Optional[int] = None
    ) -> str:
        """Generate a pre-signed URL for downloading a file from S3
        
        Args:
            object_key: The S3 object key (path) for the file
            expiration: URL expiration time in seconds (default from settings)
            
        Returns:
            Pre-signed download URL
            
        Raises:
            ClientError: If URL generation fails
        """
        if expiration is None:
            expiration = self.settings.s3_presigned_url_expiration
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned download URL for: {object_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {e}")
            raise
    
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload a file directly to S3
        
        Args:
            file_path: Local path to the file
            object_key: The S3 object key (path) for the file
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the object
            
        Returns:
            S3 object URL
            
        Raises:
            ClientError: If upload fails
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Make the object private by default
            extra_args['ACL'] = 'private'
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            # Return the S3 URL
            url = f"s3://{self.bucket_name}/{object_key}"
            logger.info(f"Uploaded file to S3: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3
        
        Args:
            object_key: The S3 object key (path) for the file
            
        Returns:
            True if deletion was successful
            
        Raises:
            ClientError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted file from S3: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise
    
    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in S3
        
        Args:
            object_key: The S3 object key (path) for the file
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {e}")
            raise
    
    def get_file_url(self, object_key: str) -> str:
        """Get the S3 URL for a file
        
        Args:
            object_key: The S3 object key (path) for the file
            
        Returns:
            S3 URL
        """
        return f"s3://{self.bucket_name}/{object_key}"
