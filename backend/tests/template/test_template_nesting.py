"""Tests for template nesting and debug functionality"""
import pytest
import asyncio
from sqlalchemy.orm import Session
from app.services.renderer import template_renderer
from app.models.db_models import Template
from app.database import SessionLocal


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def create_test_templates(db_session: Session):
    """Create test templates for nesting tests"""
    templates = []
    
    # Template 1: Simple child template
    template1 = Template(
        id="test_child_simple",
        name="Simple Child Template",
        description="A simple child template",
        template_content="Child content: {{child_var}}",
        metadata_json={
            "child_var": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Child variable",
                "ui_config": {
                    "input_type": "text"
                }
            }
        }
    )
    db_session.add(template1)
    templates.append(template1)
    
    # Template 2: Parent template with include
    template2 = Template(
        id="test_parent_simple",
        name="Simple Parent Template",
        description="A parent template with one include",
        template_content='# Parent Title\n\n{% include "test_child_simple" %}',
        metadata_json={
            "parent_var": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Parent variable",
                "ui_config": {
                    "input_type": "text"
                }
            }
        }
    )
    db_session.add(template2)
    templates.append(template2)
    
    # Template 3: Nested child (level 2)
    template3 = Template(
        id="test_nested_level2",
        name="Nested Level 2",
        description="Second level nested template",
        template_content="Level 2: {{level2_var}}",
        metadata_json={
            "level2_var": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Level 2 variable",
                "ui_config": {
                    "input_type": "text"
                }
            }
        }
    )
    db_session.add(template3)
    templates.append(template3)
    
    # Template 4: Nested child (level 1) that includes level 2
    template4 = Template(
        id="test_nested_level1",
        name="Nested Level 1",
        description="First level nested template",
        template_content='Level 1: {{level1_var}}\n\n{% include "test_nested_level2" %}',
        metadata_json={
            "level1_var": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Level 1 variable",
                "ui_config": {
                    "input_type": "text"
                }
            }
        }
    )
    db_session.add(template4)
    templates.append(template4)
    
    # Template 5: Parent for nested test
    template5 = Template(
        id="test_nested_parent",
        name="Nested Parent",
        description="Parent template for nested test",
        template_content='# Nested Test\n\n{% include "test_nested_level1" %}',
        metadata_json={}
    )
    db_session.add(template5)
    templates.append(template5)
    
    # Template 6: Circular A (includes B)
    template6 = Template(
        id="test_circular_a",
        name="Circular A",
        description="Template A for circular test",
        template_content='A includes B:\n{% include "test_circular_b" %}',
        metadata_json={}
    )
    db_session.add(template6)
    templates.append(template6)
    
    # Template 7: Circular B (includes A)
    template7 = Template(
        id="test_circular_b",
        name="Circular B",
        description="Template B for circular test",
        template_content='B includes A:\n{% include "test_circular_a" %}',
        metadata_json={}
    )
    db_session.add(template7)
    templates.append(template7)
    
    db_session.commit()
    
    yield templates
    
    # Cleanup
    for template in templates:
        db_session.delete(template)
    db_session.commit()


@pytest.mark.asyncio
async def test_simple_template_include(db_session: Session, create_test_templates):
    """Test simple template inclusion"""
    parent_template = '# Parent Title\n\n{% include "test_child_simple" %}'
    nested_user_inputs = {
        "test_parent_simple": {"parent_var": "Parent Value"},
        "test_child_simple": {"child_var": "Child Value"}
    }
    
    resolved = await template_renderer._resolve_includes(
        parent_template,
        db_session,
        nested_user_inputs,
        "test_parent_simple"
    )
    
    assert "Child content: Child Value" in resolved
    assert "{% include" not in resolved  # Include tag should be replaced


@pytest.mark.asyncio
async def test_nested_includes(db_session: Session, create_test_templates):
    """Test nested template inclusion (A includes B, B includes C)"""
    parent_template = '# Nested Test\n\n{% include "test_nested_level1" %}'
    nested_user_inputs = {
        "test_nested_parent": {},
        "test_nested_level1": {"level1_var": "L1 Value"},
        "test_nested_level2": {"level2_var": "L2 Value"}
    }
    
    resolved = await template_renderer._resolve_includes(
        parent_template,
        db_session,
        nested_user_inputs,
        "test_nested_parent"
    )
    
    assert "Level 1: L1 Value" in resolved
    assert "Level 2: L2 Value" in resolved
    assert "{% include" not in resolved


@pytest.mark.asyncio
async def test_circular_include_detection(db_session: Session, create_test_templates):
    """Test circular include detection"""
    template_content = '# Start\n\n{% include "test_circular_a" %}'
    
    resolved = await template_renderer._resolve_includes(
        template_content,
        db_session,
        {},
        "test_main"
    )
    
    assert "ERROR: Circular include detected" in resolved


@pytest.mark.asyncio
async def test_nonexistent_template_include(db_session: Session):
    """Test including a non-existent template"""
    template_content = '# Test\n\n{% include "nonexistent_template" %}'
    
    resolved = await template_renderer._resolve_includes(
        template_content,
        db_session,
        {},
        "test_main"
    )
    
    assert "ERROR: Template 'nonexistent_template' not found" in resolved


@pytest.mark.asyncio
async def test_independent_variable_execution(db_session: Session, create_test_templates):
    """Test that sub-templates execute variables independently"""
    # This test verifies that child templates have their own ExecutionContext
    parent_template = '# Parent\n\n{% include "test_child_simple" %}'
    
    # Only provide child_var for child template
    nested_user_inputs = {
        "test_parent": {},
        "test_child_simple": {"child_var": "Child Value Only"}
    }
    
    # This should not fail even though parent_var is not provided
    # because child template is executed independently
    resolved = await template_renderer._resolve_includes(
        parent_template,
        db_session,
        nested_user_inputs,
        "test_parent"
    )
    
    assert "Child content: Child Value Only" in resolved


@pytest.mark.asyncio
async def test_multiple_includes_same_template(db_session: Session, create_test_templates):
    """Test including the same template multiple times"""
    template_content = '''# Multiple Includes

{% include "test_child_simple" %}

---

{% include "test_child_simple" %}
'''
    
    nested_user_inputs = {
        "test_main": {},
        "test_child_simple": {"child_var": "Shared Value"}
    }
    
    resolved = await template_renderer._resolve_includes(
        template_content,
        db_session,
        nested_user_inputs,
        "test_main"
    )
    
    # The child template should be rendered twice
    assert resolved.count("Child content: Shared Value") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

