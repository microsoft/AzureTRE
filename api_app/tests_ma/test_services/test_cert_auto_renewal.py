import pytest
import json
from unittest.mock import patch, MagicMock

from jsonschema import validate, ValidationError
from services.schema_service import enrich_template


class TestCertAutoRenewal:
    """Test certificate auto-renewal functionality."""

    @pytest.fixture
    def cert_template_schema(self):
        """Sample certificate template schema with auto-renewal parameters."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "https://github.com/microsoft/AzureTRE/templates/shared_services/certs/template_schema.json",
            "type": "object",
            "title": "Certificate Service",
            "description": "Provides SSL Certs for a specified internal domain",
            "required": [
                "domain_prefix",
                "cert_name"
            ],
            "properties": {
                "display_name": {
                    "type": "string",
                    "title": "Name for the workspace service",
                    "description": "The name of the workspace service to be displayed to users",
                    "default": "Certificate Service",
                    "updateable": True
                },
                "domain_prefix": {
                    "type": "string",
                    "title": "Domain prefix",
                    "description": "The FQDN prefix to generate a certificate for"
                },
                "cert_name": {
                    "type": "string",
                    "title": "Cert name", 
                    "description": "What to call the certificate exported to KeyVault"
                },
                "enable_auto_renewal": {
                    "type": "boolean",
                    "title": "Enable Auto-renewal",
                    "description": "Enable automatic renewal of the certificate before expiry",
                    "default": False,
                    "updateable": True
                },
                "renewal_threshold_days": {
                    "type": "integer",
                    "title": "Renewal threshold (days)",
                    "description": "Number of days before expiry to trigger renewal",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 60,
                    "updateable": True
                },
                "renewal_schedule_cron": {
                    "type": "string",
                    "title": "Renewal schedule (cron)",
                    "description": "Cron expression for checking certificate expiry",
                    "default": "0 2 * * 0",
                    "updateable": True
                }
            }
        }

    def test_auto_renewal_schema_validation_success(self, cert_template_schema):
        """Test that valid auto-renewal parameters pass schema validation."""
        valid_payload = {
            "domain_prefix": "nexus",
            "cert_name": "nexus-ssl",
            "enable_auto_renewal": True,
            "renewal_threshold_days": 30,
            "renewal_schedule_cron": "0 2 * * 0"
        }
        
        # Should not raise ValidationError
        validate(instance=valid_payload, schema=cert_template_schema)

    def test_auto_renewal_schema_validation_with_defaults(self, cert_template_schema):
        """Test that minimal payload with defaults works."""
        minimal_payload = {
            "domain_prefix": "test",
            "cert_name": "test-cert"
        }
        
        # Should not raise ValidationError
        validate(instance=minimal_payload, schema=cert_template_schema)

    def test_auto_renewal_threshold_validation(self, cert_template_schema):
        """Test that renewal threshold validation works."""
        # Test invalid threshold - too low
        with pytest.raises(ValidationError):
            invalid_payload = {
                "domain_prefix": "test",
                "cert_name": "test-cert", 
                "renewal_threshold_days": 0
            }
            validate(instance=invalid_payload, schema=cert_template_schema)
        
        # Test invalid threshold - too high
        with pytest.raises(ValidationError):
            invalid_payload = {
                "domain_prefix": "test",
                "cert_name": "test-cert",
                "renewal_threshold_days": 100
            }
            validate(instance=invalid_payload, schema=cert_template_schema)
        
        # Test valid thresholds
        for valid_threshold in [1, 15, 30, 45, 60]:
            valid_payload = {
                "domain_prefix": "test",
                "cert_name": "test-cert",
                "renewal_threshold_days": valid_threshold
            }
            validate(instance=valid_payload, schema=cert_template_schema)

    def test_auto_renewal_updateable_fields(self, cert_template_schema):
        """Test that auto-renewal fields are marked as updateable."""
        properties = cert_template_schema["properties"]
        
        updateable_fields = [
            "enable_auto_renewal",
            "renewal_threshold_days", 
            "renewal_schedule_cron"
        ]
        
        for field in updateable_fields:
            assert properties[field].get("updateable", False) is True, \
                f"Field {field} should be updateable"

    def test_auto_renewal_default_values(self, cert_template_schema):
        """Test that auto-renewal fields have correct default values."""
        properties = cert_template_schema["properties"]
        
        expected_defaults = {
            "enable_auto_renewal": False,
            "renewal_threshold_days": 30,
            "renewal_schedule_cron": "0 2 * * 0"
        }
        
        for field, expected_default in expected_defaults.items():
            actual_default = properties[field].get("default")
            assert actual_default == expected_default, \
                f"Field {field} should have default value {expected_default}, got {actual_default}"

    def test_missing_required_fields(self, cert_template_schema):
        """Test that missing required fields fail validation."""
        # Missing domain_prefix
        with pytest.raises(ValidationError):
            validate(instance={"cert_name": "test"}, schema=cert_template_schema)
        
        # Missing cert_name
        with pytest.raises(ValidationError):
            validate(instance={"domain_prefix": "test"}, schema=cert_template_schema)

    @pytest.mark.parametrize("auto_renewal_enabled,threshold,cron", [
        (True, 7, "0 1 * * *"),    # Daily at 1 AM
        (True, 14, "0 2 * * 1"),   # Weekly on Monday at 2 AM  
        (True, 45, "0 3 1 * *"),   # Monthly on 1st at 3 AM
        (False, 30, "0 2 * * 0"),  # Disabled with defaults
    ])
    def test_auto_renewal_parameter_combinations(self, cert_template_schema, auto_renewal_enabled, threshold, cron):
        """Test various combinations of auto-renewal parameters."""
        payload = {
            "domain_prefix": "test",
            "cert_name": "test-cert",
            "enable_auto_renewal": auto_renewal_enabled,
            "renewal_threshold_days": threshold,
            "renewal_schedule_cron": cron
        }
        
        # Should not raise ValidationError
        validate(instance=payload, schema=cert_template_schema)

    def test_type_validation(self, cert_template_schema):
        """Test that incorrect types fail validation."""
        # Wrong type for enable_auto_renewal
        with pytest.raises(ValidationError):
            validate(instance={
                "domain_prefix": "test",
                "cert_name": "test-cert", 
                "enable_auto_renewal": "true"  # Should be boolean
            }, schema=cert_template_schema)
        
        # Wrong type for renewal_threshold_days
        with pytest.raises(ValidationError):
            validate(instance={
                "domain_prefix": "test",
                "cert_name": "test-cert",
                "renewal_threshold_days": "30"  # Should be integer
            }, schema=cert_template_schema)
        
        # Wrong type for renewal_schedule_cron
        with pytest.raises(ValidationError):
            validate(instance={
                "domain_prefix": "test", 
                "cert_name": "test-cert",
                "renewal_schedule_cron": 123  # Should be string
            }, schema=cert_template_schema)