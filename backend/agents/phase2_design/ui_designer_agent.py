"""
UI Designer Agent - Creates UI/UX design and component architecture
Phase 2: Design & Planning
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole
from models.ui_schemas import UIDesign, UIPageDesign, UIComponentDesign

logger = structlog.get_logger()


class UIDesignerAgent(BaseAgent):
    """
    Creates comprehensive UI/UX designs:
    - Design system selection
    - Color scheme and typography
    - Page/screen designs
    - Component architecture
    - Navigation structure
    - Responsive design strategy
    - Accessibility considerations
    - User flows and interactions
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.UI_DESIGNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert UI/UX Designer and Frontend Architect. Your role is to:

1. Design intuitive, accessible user interfaces
2. Select appropriate design systems and frameworks
3. Create cohesive component architectures
4. Plan responsive layouts
5. Design user flows and interactions
6. Ensure accessibility (WCAG compliance)
7. Consider mobile-first design

Your designs should:
- Follow modern UI/UX best practices
- Be accessible (WCAG 2.1 AA minimum)
- Support responsive design
- Have clear component hierarchies
- Follow atomic design principles (atoms, molecules, organisms)
- Consider performance (lazy loading, code splitting)
- Support dark mode (if applicable)
- Have consistent visual language

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when designing UI/UX:

**Step 1: Understand User Needs**
- Who are the users? (roles, technical level)
- What are their goals? (what do they want to accomplish?)
- What are the key user flows?
- What devices will they use? (desktop, mobile, tablet)

**Step 2: Choose Design System**
**CRITICAL: For Next.js projects, ALWAYS use Tailwind CSS**

- **Tailwind CSS (REQUIRED for Next.js)**: Utility-first CSS framework
  - Extremely customizable and modern
  - Excellent performance (only includes used classes)
  - Perfect for Next.js with built-in support
  - Responsive design made easy
  - Modern design patterns (dark mode, animations, etc.)
  - Small bundle size with tree-shaking

Other options (only if not using Next.js):
- Material-UI: Good for Material Design
- Bootstrap: Quick prototypes
- Chakra UI: Component library with accessibility

**Step 3: Design Visual System**
- Color palette: What emotions/brand does this convey?
- Typography: Readability, hierarchy, web-safe fonts
- Spacing system: Consistent margins, padding (4px, 8px, 16px, etc.)
- Visual elements: Borders, shadows, radius for modern feel

**Step 4: Design Pages/Screens**
- List all pages needed (based on functional requirements)
- For each page: What's the purpose? What data is shown? What actions?
- Sketch layout: Header, main content, sidebar, footer
- Identify components needed on each page

**Step 5: Design Component Architecture**
- Identify reusable components (buttons, cards, forms, etc.)
- Follow atomic design: atoms → molecules → organisms → templates
- Define props: What data does each component need?
- Define state: What changes? What's interactive?
- Define events: What user actions trigger what?

**Step 6: Plan Navigation**
- What's the information architecture?
- How do users move between pages? (nav bar, sidebar, breadcrumbs)
- What's the menu structure?
- How does routing work?

**Step 7: Design for Responsiveness**
- Mobile-first approach: Design for small screens first
- Breakpoints: When does layout change? (640px, 768px, 1024px, 1280px)
- What's different on mobile vs. desktop?
- Touch targets: Are buttons large enough (44px minimum)?

**Step 8: Ensure Accessibility**
- ARIA labels: Are all interactive elements labeled?
- Keyboard navigation: Can you navigate with Tab, Enter, Escape?
- Color contrast: Do colors meet 4.5:1 ratio?
- Screen readers: Will it read correctly?
- Focus indicators: Can you see what's focused?

**Step 9: Design User Flows**
- Map key user journeys (e.g., sign up → verify → dashboard)
- What's the happy path?
- What are the error states? (form validation, network errors)
- What loading states are needed?

**IMPORTANT: Think step-by-step through Steps 1-9 above, then provide JSON.**

First, systematically design the UI/UX with detailed reasoning.

For each project, design:

1. **DESIGN SYSTEM**:
   **CRITICAL: For Next.js 14 projects, you MUST use Tailwind CSS**
   - Framework: Tailwind CSS (utility-first, highly customizable)
   - Configuration: tailwind.config.ts with extended theme
   - Plugins: Consider @tailwindcss/forms, @tailwindcss/typography if needed
   - Custom utilities: Define reusable component classes

2. **VISUAL DESIGN with Tailwind CSS**:
   - Color palette using Tailwind color system:
     * Primary: blue-600, blue-700 (hover states)
     * Secondary: purple-600, purple-700
     * Success: green-600, green-700
     * Warning: yellow-600, yellow-700
     * Danger: red-600, red-700
     * Background: gray-900, gray-800, gray-700 (dark mode)
     * Text: white, gray-300, gray-400, gray-500
   
   - Typography using Tailwind classes:
     * Font families: font-sans (Inter), font-mono (Fira Code)
     * Text sizes: text-xs, text-sm, text-base, text-lg, text-xl, text-2xl, text-3xl
     * Font weights: font-normal, font-medium, font-semibold, font-bold
   
   - Spacing system (Tailwind's 4px scale):
     * p-2, p-4, p-6, p-8 (padding)
     * m-2, m-4, m-6, m-8 (margin)
     * gap-2, gap-4, gap-6 (flex/grid gaps)
   
   - Modern design elements:
     * Border radius: rounded-lg, rounded-xl
     * Shadows: shadow-lg, shadow-xl
     * Backdrop blur: backdrop-blur-sm, backdrop-blur-lg
     * Transitions: transition-all duration-200

3. **PAGE DESIGNS**:
   - All pages/screens needed
   - Layout for each page
   - Components on each page
   - Data requirements

4. **COMPONENT ARCHITECTURE**:
   - Reusable components
   - Component hierarchy
   - Props and state
   - Component interactions

5. **NAVIGATION**:
   - Navigation structure
   - Menu design
   - Routing strategy

6. **RESPONSIVE DESIGN with Tailwind Breakpoints**:
   **Use Tailwind's mobile-first responsive prefixes:**
   - Base (mobile): No prefix, applies to all sizes
   - sm: @media (min-width: 640px) - Small tablets
   - md: @media (min-width: 768px) - Tablets
   - lg: @media (min-width: 1024px) - Desktops
   - xl: @media (min-width: 1280px) - Large desktops
   - 2xl: @media (min-width: 1536px) - Extra large screens
   
   **Examples:**
   - Width: w-full md:w-1/2 lg:w-1/3 (full on mobile, half on tablet, third on desktop)
   - Text: text-sm md:text-base lg:text-lg (responsive text sizes)
   - Grid: grid-cols-1 md:grid-cols-2 lg:grid-cols-3 (responsive grid)
   - Padding: px-4 md:px-6 lg:px-8 (responsive spacing)
   - Hidden: hidden md:block (hide on mobile, show on desktop)
   
   - Touch targets: Minimum 44px (p-3 or py-3) for mobile buttons
   - Mobile navigation: Hamburger menu, slide-out drawer
   - Desktop navigation: Full horizontal menu

7. **ACCESSIBILITY**:
   - ARIA labels
   - Keyboard navigation
   - Screen reader support
   - Color contrast

8. **USER FLOWS**:
   - Key user journeys
   - Interactive states
   - Error states

Then respond in JSON format:
{
    "reasoning": "My step-by-step UI/UX design process: [user needs analysis, design system selection, visual design decisions, etc.]...",
    "design_system": "Tailwind CSS (REQUIRED for Next.js) - utility-first CSS framework with excellent customization and performance",
    "color_scheme": {
        "primary": "blue-600 (hover: blue-700)",
        "secondary": "purple-600 (hover: purple-700)",
        "success": "green-600",
        "danger": "red-600",
        "background": "gray-900, gray-800, gray-700",
        "text": "white, gray-300, gray-400"
    },
    "typography": {
        "heading": "font-sans (Inter) with font-bold",
        "body": "font-sans (Inter) with font-normal",
        "code": "font-mono (Fira Code)"
    },
    "tailwind_config": {
        "extended_colors": "brand palette",
        "custom_animations": "fade-in, slide-in",
        "custom_utilities": "btn-primary, card, input classes"
    },
    "layout_pattern": "Flexbox (flex, flex-col) and CSS Grid (grid, grid-cols-*) with Tailwind utilities",
    "pages": [
        {
            "page_name": "HomePage",
            "route": "/",
            "purpose": "Landing page",
            "layout": "Hero section + features grid + CTA",
            "components": ["Navbar", "Hero", "FeatureCard", "Footer"],
            "data_requirements": ["featured items"],
            "interactions": ["scroll to section", "click CTA"]
        }
    ],
    "components": [
        {
            "component_name": "Navbar",
            "component_type": "navigation",
            "purpose": "Main navigation",
            "props": ["links", "logo"],
            "state": ["isMenuOpen"],
            "events": ["onMenuToggle"],
            "children": ["NavLink", "Logo"],
            "tailwind_classes": "sticky top-0 z-50 bg-gray-900/80 backdrop-blur-lg border-b border-gray-800",
            "responsive_behavior": "Full menu on desktop (md:flex), hamburger on mobile"
        },
        {
            "component_name": "Button",
            "component_type": "atom",
            "purpose": "Reusable button component",
            "props": ["variant", "size", "children", "onClick", "disabled"],
            "tailwind_classes": "px-6 py-3 rounded-lg font-semibold transition-all duration-200 hover:scale-105 disabled:opacity-50",
            "variants": {
                "primary": "bg-blue-600 hover:bg-blue-700 text-white",
                "secondary": "bg-gray-700 hover:bg-gray-600 text-white",
                "danger": "bg-red-600 hover:bg-red-700 text-white"
            }
        },
        {
            "component_name": "Card",
            "component_type": "molecule",
            "purpose": "Content container with modern styling",
            "tailwind_classes": "bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all"
        }
    ],
    "navigation": {
        "type": "top navbar + sidebar on mobile",
        "structure": {
            "Home": "/",
            "About": "/about"
        }
    },
    "responsive_strategy": "Mobile-first using Tailwind breakpoints (sm:640px, md:768px, lg:1024px, xl:1280px). Examples: w-full md:w-1/2 lg:w-1/3, text-sm md:text-base lg:text-lg, grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    "accessibility": [
        "ARIA labels on all interactive elements",
        "Keyboard navigation support",
        "Min 4.5:1 color contrast"
    ],
    "user_flows": [
        "User lands -> views hero -> clicks CTA -> fills form -> submits"
    ]
}

Design beautiful, functional, accessible UIs.
Think step-by-step. Show your UI/UX design reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create UI/UX design

        Args:
            task_data: Contains requirements, HLD, modules, etc.

        Returns:
            Complete UI design
        """
        activity = await self.start_activity("Designing UI/UX and components")

        try:
            description = task_data.get("description", "")
            requirements = task_data.get("requirements", {})
            hld = task_data.get("hld", {})
            modules = task_data.get("modules", [])
            language = task_data.get("language", "python")
            framework = task_data.get("framework", "")

            logger.info("ui_design_started", language=language, framework=framework)

            prompt = self._build_ui_design_prompt(
                description, requirements, hld, modules, language, framework
            )

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher temperature for creative design
                max_tokens=3500
            )

            ui_design_data = self._parse_ui_design_response(response)
            ui_design = UIDesign(**ui_design_data)

            await self.complete_activity("completed")

            logger.info(
                "ui_design_completed",
                pages_count=len(ui_design.pages),
                components_count=len(ui_design.components)
            )

            return {
                "ui_design": ui_design.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("ui_design_failed", error=str(e))
            raise

    def _build_ui_design_prompt(
        self,
        description: str,
        requirements: Dict,
        hld: Dict,
        modules: List,
        language: str,
        framework: str
    ) -> str:
        """Build UI design prompt"""
        functional_reqs = requirements.get("functional", [])
        user_stories = requirements.get("user_stories", [])

        # Determine if this needs a UI
        needs_ui = any(keyword in description.lower() for keyword in [
            "web", "app", "ui", "interface", "frontend", "dashboard", "portal",
            "website", "mobile", "desktop"
        ]) or "ui" in description.lower() or "interface" in description.lower()

        # Infer UI framework
        ui_framework = framework if framework and framework.lower() in [
            "react", "vue", "angular", "svelte", "next", "nuxt"
        ] else self._infer_ui_framework(language, description)

        prompt = f"""Design the UI/UX for the following application:

PROJECT DESCRIPTION:
{description}

NEEDS UI: {needs_ui}

FUNCTIONAL REQUIREMENTS:
{self._format_list(functional_reqs[:10])}

USER STORIES:
{self._format_list(user_stories[:5])}

ARCHITECTURE:
{hld.get('system_overview', 'Not specified')}

MAJOR COMPONENTS:
{', '.join(hld.get('major_components', []))}

TECHNOLOGY:
- Language: {language}
- Framework: {ui_framework}

Based on this, create a comprehensive UI/UX design:

1. **DESIGN SYSTEM SELECTION**:
   - Choose the best fit for {ui_framework}
   - Consider the project requirements
   - Justify your choice

2. **VISUAL DESIGN**:
   - Professional color scheme
   - Typography that matches the brand feel
   - Consistent spacing and sizing

3. **PAGE/SCREEN DESIGNS**:
   - Design ALL pages needed based on requirements
   - For each page: layout, components, data, interactions

4. **COMPONENT ARCHITECTURE**:
   - Reusable components following atomic design
   - Component props and state
   - Component relationships

5. **NAVIGATION**:
   - Clear navigation structure
   - Easy to use

6. **RESPONSIVE DESIGN**:
   - Mobile-first strategy
   - Breakpoints
   - Adaptation strategy

7. **ACCESSIBILITY**:
   - WCAG 2.1 AA compliance
   - Keyboard navigation
   - Screen reader support

8. **USER FLOWS**:
   - Key user journeys
   - Happy paths and error handling

If this doesn't need a UI (e.g., it's a pure API), design a minimal admin/status UI.

Respond in valid JSON format."""

        return prompt

    def _infer_ui_framework(self, language: str, description: str) -> str:
        """Infer appropriate UI framework"""
        lang_lower = language.lower()
        desc_lower = description.lower()

        if "react" in desc_lower:
            return "React"
        elif "vue" in desc_lower:
            return "Vue"
        elif "angular" in desc_lower:
            return "Angular"
        elif lang_lower in ["javascript", "typescript"]:
            return "React"  # Default for JS/TS
        elif lang_lower == "python":
            if "dash" in desc_lower:
                return "Plotly Dash"
            elif "streamlit" in desc_lower:
                return "Streamlit"
            else:
                return "React (with Python backend)"
        else:
            return "React"  # Default

    def _format_list(self, items: list) -> str:
        """Format list"""
        if not items:
            return "None specified"
        return "\n".join([f"- {item}" for item in items])

    def _parse_ui_design_response(self, response: str) -> Dict[str, Any]:
        """Parse UI design response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            ui_data = json.loads(response)

            # Validate required fields
            required_fields = [
                "design_system", "color_scheme", "typography",
                "layout_pattern", "pages", "components", "navigation",
                "responsive_strategy", "accessibility", "user_flows"
            ]

            for field in required_fields:
                if field not in ui_data:
                    logger.warning(f"Missing UI field: {field}")
                    # Provide defaults
                    if field == "pages":
                        ui_data[field] = []
                    elif field == "components":
                        ui_data[field] = []
                    elif field == "accessibility":
                        ui_data[field] = ["WCAG 2.1 AA compliance planned"]
                    elif field == "user_flows":
                        ui_data[field] = ["Basic user flow"]
                    elif field in ["color_scheme", "typography", "navigation"]:
                        ui_data[field] = {}
                    else:
                        ui_data[field] = f"Default {field}"

            return ui_data

        except json.JSONDecodeError as e:
            logger.error("ui_design_parse_error", error=str(e))

            # Fallback minimal UI design
            return {
                "design_system": "Material-UI with React",
                "color_scheme": {
                    "primary": "#1976d2",
                    "secondary": "#dc004e",
                    "background": "#ffffff",
                    "text": "#212121"
                },
                "typography": {
                    "heading": "Roboto",
                    "body": "Roboto"
                },
                "layout_pattern": "Responsive grid layout",
                "pages": [
                    {
                        "page_name": "HomePage",
                        "route": "/",
                        "purpose": "Main page",
                        "layout": "Standard layout",
                        "components": ["Header", "Content", "Footer"],
                        "data_requirements": [],
                        "interactions": ["Navigation"]
                    }
                ],
                "components": [
                    {
                        "component_name": "Header",
                        "component_type": "navigation",
                        "purpose": "Top navigation",
                        "props": [],
                        "state": [],
                        "events": [],
                        "children": []
                    }
                ],
                "navigation": {
                    "type": "top navbar",
                    "structure": {"Home": "/"}
                },
                "responsive_strategy": "Mobile-first with standard breakpoints",
                "accessibility": ["WCAG 2.1 AA compliance"],
                "user_flows": ["User navigates through app"]
            }
