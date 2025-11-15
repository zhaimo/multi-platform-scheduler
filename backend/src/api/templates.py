"""Post template management API endpoints"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from src.database import get_db
from src.utils.auth import get_current_user
from src.models.database_models import User, PostTemplate

router = APIRouter(prefix="/api/templates", tags=["templates"])


# Pydantic schemas
class PlatformTemplateConfig(BaseModel):
    """Platform-specific template configuration"""
    caption: str = Field(..., min_length=1, description="Post caption template")
    hashtags: List[str] = Field(default_factory=list, description="List of hashtags")
    privacy_level: str = Field(default="public", description="Privacy level (public, private, friends)")
    disable_comments: bool = Field(default=False, description="Disable comments")
    disable_duet: bool = Field(default=False, description="Disable duet (TikTok)")
    disable_stitch: bool = Field(default=False, description="Disable stitch (TikTok)")


class CreateTemplateRequest(BaseModel):
    """Create template request schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    platform_configs: Dict[str, PlatformTemplateConfig] = Field(
        ...,
        description="Platform-specific configurations (e.g., {'tiktok': {...}, 'youtube': {...}})"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Viral Video Template",
                "platform_configs": {
                    "tiktok": {
                        "caption": "Check this out! #viral #trending",
                        "hashtags": ["viral", "trending", "fyp"],
                        "privacy_level": "public",
                        "disable_comments": False
                    },
                    "youtube": {
                        "caption": "Amazing content! Don't forget to like and subscribe!",
                        "hashtags": ["shorts", "viral"],
                        "privacy_level": "public",
                        "disable_comments": False
                    }
                }
            }
        }


class UpdateTemplateRequest(BaseModel):
    """Update template request schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    platform_configs: Optional[Dict[str, PlatformTemplateConfig]] = Field(
        None,
        description="Platform-specific configurations"
    )


class TemplateResponse(BaseModel):
    """Template response schema"""
    id: UUID
    user_id: UUID
    name: str
    platform_configs: Dict[str, Any]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new post template
    
    Templates allow you to save reusable configurations for posting to multiple platforms.
    Each template can contain platform-specific captions, hashtags, and settings.
    
    Args:
        request: Template creation request with name and platform configs
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Created template object
    """
    try:
        # Convert PlatformTemplateConfig to dict format for storage
        platform_configs_dict = {}
        for platform_name, config in request.platform_configs.items():
            platform_configs_dict[platform_name] = {
                "caption": config.caption,
                "hashtags": config.hashtags,
                "privacy_level": config.privacy_level,
                "disable_comments": config.disable_comments,
                "disable_duet": config.disable_duet,
                "disable_stitch": config.disable_stitch
            }
        
        # Create template
        template = PostTemplate(
            user_id=current_user.id,
            name=request.name,
            platform_configs=platform_configs_dict
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        return TemplateResponse(
            id=template.id,
            user_id=template.user_id,
            name=template.name,
            platform_configs=template.platform_configs,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat()
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's post templates
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of template objects
    """
    try:
        # Query templates for current user
        result = await db.execute(
            select(PostTemplate)
            .where(PostTemplate.user_id == current_user.id)
            .order_by(PostTemplate.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        templates = result.scalars().all()
        
        return [
            TemplateResponse(
                id=template.id,
                user_id=template.user_id,
                name=template.name,
                platform_configs=template.platform_configs,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat()
            )
            for template in templates
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific template by ID
    
    Args:
        template_id: Template ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Template object
    """
    try:
        result = await db.execute(
            select(PostTemplate)
            .where(
                PostTemplate.id == template_id,
                PostTemplate.user_id == current_user.id
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return TemplateResponse(
            id=template.id,
            user_id=template.user_id,
            name=template.name,
            platform_configs=template.platform_configs,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    request: UpdateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a template
    
    Args:
        template_id: Template ID
        request: Update request with optional name and platform configs
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated template object
    """
    try:
        # Get template
        result = await db.execute(
            select(PostTemplate)
            .where(
                PostTemplate.id == template_id,
                PostTemplate.user_id == current_user.id
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Update fields
        if request.name is not None:
            template.name = request.name
        
        if request.platform_configs is not None:
            # Convert PlatformTemplateConfig to dict format for storage
            platform_configs_dict = {}
            for platform_name, config in request.platform_configs.items():
                platform_configs_dict[platform_name] = {
                    "caption": config.caption,
                    "hashtags": config.hashtags,
                    "privacy_level": config.privacy_level,
                    "disable_comments": config.disable_comments,
                    "disable_duet": config.disable_duet,
                    "disable_stitch": config.disable_stitch
                }
            template.platform_configs = platform_configs_dict
        
        await db.commit()
        await db.refresh(template)
        
        return TemplateResponse(
            id=template.id,
            user_id=template.user_id,
            name=template.name,
            platform_configs=template.platform_configs,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a template
    
    Args:
        template_id: Template ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        No content on success
    """
    try:
        # Get template
        result = await db.execute(
            select(PostTemplate)
            .where(
                PostTemplate.id == template_id,
                PostTemplate.user_id == current_user.id
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Delete template
        await db.delete(template)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )
