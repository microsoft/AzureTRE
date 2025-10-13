#!/usr/bin/env python3
"""
Test script to validate the certificate service template schema
includes the new auto-renewal parameters.
"""
import json
import jsonschema
from jsonschema import validate


def test_schema_validation():
    """Test that the template schema is valid and includes auto-renewal parameters."""
    # Load the template schema
    with open('template_schema.json', 'r') as f:
        schema = json.load(f)
    
    # Validate the schema itself is valid JSON Schema
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        print("✅ Schema is valid JSON Schema")
    except jsonschema.SchemaError as e:
        print(f"❌ Schema validation failed: {e}")
        return False
    
    # Test that required fields are present
    required_fields = ['domain_prefix', 'cert_name']
    assert all(field in schema.get('required', []) for field in required_fields), \
        f"Required fields missing: {required_fields}"
    print("✅ Required fields are present")
    
    # Test that auto-renewal parameters exist with correct types
    properties = schema.get('properties', {})
    
    auto_renewal_params = {
        'enable_auto_renewal': 'boolean',
        'renewal_threshold_days': 'integer',
        'renewal_schedule_cron': 'string'
    }
    
    for param, expected_type in auto_renewal_params.items():
        assert param in properties, f"Parameter {param} not found in schema"
        assert properties[param]['type'] == expected_type, \
            f"Parameter {param} has wrong type. Expected: {expected_type}, Got: {properties[param]['type']}"
        print(f"✅ Parameter {param} has correct type ({expected_type})")
    
    # Test default values
    assert properties['enable_auto_renewal']['default'] == False
    assert properties['renewal_threshold_days']['default'] == 30
    assert properties['renewal_schedule_cron']['default'] == "0 2 * * 0"
    print("✅ Default values are correct")
    
    # Test validation constraints
    threshold_param = properties['renewal_threshold_days']
    assert threshold_param['minimum'] == 1
    assert threshold_param['maximum'] == 60
    print("✅ Validation constraints are correct")
    
    # Test that auto-renewal fields are updateable
    updateable_fields = ['enable_auto_renewal', 'renewal_threshold_days', 'renewal_schedule_cron']
    for field in updateable_fields:
        assert properties[field].get('updateable', False), \
            f"Field {field} should be updateable"
    print("✅ Auto-renewal fields are updateable")
    
    # Test valid input validation
    valid_input = {
        "domain_prefix": "test",
        "cert_name": "test-cert",
        "enable_auto_renewal": True,
        "renewal_threshold_days": 15,
        "renewal_schedule_cron": "0 3 * * 1"
    }
    
    try:
        validate(instance=valid_input, schema=schema)
        print("✅ Valid input passes schema validation")
    except jsonschema.ValidationError as e:
        print(f"❌ Valid input failed validation: {e}")
        return False
    
    # Test invalid input validation
    invalid_inputs = [
        {
            "domain_prefix": "test",
            "cert_name": "test-cert",
            "renewal_threshold_days": 0  # Too low
        },
        {
            "domain_prefix": "test", 
            "cert_name": "test-cert",
            "renewal_threshold_days": 100  # Too high
        },
        {
            "cert_name": "test-cert"  # Missing required domain_prefix
        }
    ]
    
    for i, invalid_input in enumerate(invalid_inputs):
        try:
            validate(instance=invalid_input, schema=schema)
            print(f"❌ Invalid input {i+1} incorrectly passed validation")
            return False
        except jsonschema.ValidationError:
            print(f"✅ Invalid input {i+1} correctly failed validation")
    
    print("\n🎉 All schema validation tests passed!")
    return True


def test_porter_parameters():
    """Test that porter.yaml contains the new parameters."""
    try:
        with open('porter.yaml', 'r') as f:
            porter_content = f.read()
    except FileNotFoundError:
        print("❌ porter.yaml not found")
        return False
    
    required_params = [
        'enable_auto_renewal',
        'renewal_threshold_days', 
        'renewal_schedule_cron'
    ]
    
    for param in required_params:
        if param not in porter_content:
            print(f"❌ Parameter {param} not found in porter.yaml")
            return False
        print(f"✅ Parameter {param} found in porter.yaml")
    
    print("✅ All porter.yaml parameters are present")
    return True


if __name__ == "__main__":
    print("Testing certificate service auto-renewal schema...")
    print("=" * 50)
    
    schema_valid = test_schema_validation()
    porter_valid = test_porter_parameters()
    
    if schema_valid and porter_valid:
        print("\n🎉 All tests passed! Auto-renewal feature is ready.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        exit(1)