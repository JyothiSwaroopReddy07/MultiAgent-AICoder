# Tej - 78879925

"""
UI Design schemas
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class UIComponentDesign(BaseModel):
    """Design for a UI component"""
    component_name: str = Field(..., description="Component name")
    component_type: str = Field(..., description="Component type (button, form, card, etc)")
    purpose: str = Field(..., description="Component purpose")
    props: List[str] = Field(default=[], description="Component properties")
    state: List[str] = Field(default=[], description="State variables")
    events: List[str] = Field(default=[], description="Event handlers")
    children: List[str] = Field(default=[], description="Child components")


class UIPageDesign(BaseModel):
    """Design for a UI page/screen"""
    page_name: str = Field(..., description="Page name")
    route: str = Field(..., description="Route/path")
    purpose: str = Field(..., description="Page purpose")
    layout: str = Field(..., description="Layout description")
    components: List[str] = Field(..., description="Components used")
    data_requirements: List[str] = Field(default=[], description="Data needed")
    interactions: List[str] = Field(default=[], description="User interactions")


class UIDesign(BaseModel):
    """Complete UI/UX Design"""
    design_system: str = Field(..., description="Design system/framework (Material, Bootstrap, etc)")
    color_scheme: Dict[str, str] = Field(..., description="Color palette")
    typography: Dict[str, str] = Field(..., description="Typography choices")
    layout_pattern: str = Field(..., description="Layout pattern (grid, flex, etc)")

    pages: List[UIPageDesign] = Field(..., description="Page designs")
    components: List[UIComponentDesign] = Field(..., description="Component designs")

    navigation: Dict[str, Any] = Field(..., description="Navigation structure")
    responsive_strategy: str = Field(..., description="Responsive design approach")
    accessibility: List[str] = Field(default=[], description="Accessibility features")
    user_flows: List[str] = Field(default=[], description="Key user flows")
