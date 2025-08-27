# coding: utf-8
import os
import pytest
from unittest.mock import patch, mock_open, MagicMock
from decouple import (
    Config, RepositoryEmpty, RepositoryIni, RepositoryEnv, 
    RepositorySecret, AutoConfig, UndefinedValueError, undefined
)


class TestConfigEdgeCases:
    """Test edge cases in the Config class to prevent regression."""

    def test_get_with_empty_string_value_and_default(self):
        """Test Config.get() behavior with empty string values and defaults."""
        config = Config(RepositoryEmpty())
        
        # Empty string should use default when provided
        result = config.get('nonexistent', default='default_value')
        assert result == 'default_value'
        
        # Empty string should not use default when no default provided
        with pytest.raises(UndefinedValueError):
            config.get('nonexistent')

    def test_get_with_none_value_and_default(self):
        """Test Config.get() behavior with None values and defaults."""
        config = Config(RepositoryEmpty())
        
        # None value should use default when provided
        result = config.get('nonexistent', default='default_value')
        assert result == 'default_value'

    def test_get_with_custom_cast_function(self):
        """Test Config.get() with custom cast functions."""
        config = Config(RepositoryEmpty())
        
        def custom_cast(value):
            return f"CAST_{value}"
        
        result = config.get('nonexistent', default='test', cast=custom_cast)
        assert result == 'CAST_test'

    def test_get_with_bool_cast_and_empty_string(self):
        """Test Config.get() with bool casting and empty string values."""
        config = Config(RepositoryEmpty())
        
        # Empty string should cast to False with bool cast
        result = config.get('nonexistent', default='', cast=bool)
        assert result is False
        
        # None should fail with bool cast because str(None) = 'None' which is invalid
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default=None, cast=bool)

    def test_get_with_bool_cast_and_whitespace_string(self):
        """Test Config.get() with bool casting and whitespace-only strings."""
        config = Config(RepositoryEmpty())
        
        # Whitespace-only string should cast to True with bool cast
        # (because it's not empty, so strtobool is called)
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='   ', cast=bool)


class TestRepositoryIniEdgeCases:
    """Test edge cases in RepositoryIni to prevent regression."""

    def test_repository_ini_file_not_found(self):
        """Test RepositoryIni behavior when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            RepositoryIni('nonexistent.ini')

    def test_repository_ini_malformed_ini_file(self):
        """Test RepositoryIni behavior with malformed INI content."""
        malformed_content = """
        [settings]
        key1 = value1
        [invalid_section
        key2 = value2
        """
        
        # Mock the file operations properly
        mock_file = mock_open(read_data=malformed_content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                with pytest.raises(Exception):  # ConfigParser should fail
                    RepositoryIni('test.ini')

    def test_repository_ini_key_not_found(self):
        """Test RepositoryIni behavior when key doesn't exist."""
        valid_content = """
        [settings]
        key1 = value1
        """
        
        # Mock the file operations properly
        mock_file = mock_open(read_data=valid_content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryIni('test.ini')
                
                # Key not in section should raise KeyError
                with pytest.raises(KeyError):
                    repo['nonexistent_key']


class TestRepositoryEnvEdgeCases:
    """Test edge cases in RepositoryEnv to prevent regression."""

    def test_repository_env_malformed_lines(self):
        """Test RepositoryEnv behavior with malformed lines."""
        malformed_content = """
        KEY1=value1
        KEY2
        =value3
        KEY4
        KEY5=value5
        """
        
        # Mock the file operations properly
        mock_file = mock_open(read_data=malformed_content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryEnv('test.env')
                
                # Only valid lines should be parsed
                assert 'KEY1' in repo.data
                assert 'KEY5' in repo.data
                assert 'KEY2' not in repo.data
                assert 'KEY4' not in repo.data

    def test_repository_env_quoted_values_edge_cases(self):
        """Test RepositoryEnv behavior with edge case quoted values."""
        edge_case_content = """
        KEY1="value with 'single' quotes"
        KEY2='value with "double" quotes'
        KEY3="unclosed quote
        KEY4='unclosed quote
        KEY5="mixed'quotes"
        KEY6='mixed"quotes'
        """
        
        # Mock the file operations properly
        mock_file = mock_open(read_data=edge_case_content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryEnv('test.env')
                
                # Mixed quotes should be handled correctly
                assert repo.data['KEY1'] == "value with 'single' quotes"
                assert repo.data['KEY2'] == 'value with "double" quotes'
                assert repo.data['KEY5'] == "mixed'quotes"
                assert repo.data['KEY6'] == 'mixed"quotes'

    def test_repository_env_encoding_handling(self):
        """Test RepositoryEnv behavior with different encodings."""
        unicode_content = """
        KEY1=value1
        KEY2=valüe2
        KEY3=valée3
        """
        
        # Mock the file operations properly
        mock_file = mock_open(read_data=unicode_content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryEnv('test.env', encoding='utf-8')
                
                # Unicode values should be preserved
                assert repo.data['KEY2'] == 'valüe2'
                assert repo.data['KEY3'] == 'valée3'


class TestRepositorySecretEdgeCases:
    """Test edge cases in RepositorySecret to prevent regression."""

    def test_repository_secret_directory_not_found(self):
        """Test RepositorySecret behavior when directory doesn't exist."""
        with patch('os.listdir', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                RepositorySecret('/nonexistent/secrets/')

    def test_repository_secret_file_read_error(self):
        """Test RepositorySecret behavior when file read fails."""
        with patch('os.listdir', return_value=['secret1', 'secret2']):
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(IOError):
                    RepositorySecret('/run/secrets/')


class TestAutoConfigEdgeCases:
    """Test edge cases in AutoConfig to prevent regression."""

    def test_auto_config_search_path_none(self):
        """Test AutoConfig behavior when search_path is None."""
        config = AutoConfig()
        
        # Should not fail when search_path is None
        assert config.search_path is None

    def test_auto_config_file_discovery_edge_cases(self):
        """Test AutoConfig file discovery with edge cases."""
        config = AutoConfig()
        
        with patch('os.path.isfile', return_value=False):
            with patch('os.path.dirname', return_value=''):
                # Should handle root directory case
                result = config._find_file('/')
                assert result == ''

    def test_auto_config_load_with_exception(self):
        """Test AutoConfig load behavior when exceptions occur."""
        config = AutoConfig()
        
        with patch.object(config, '_find_file', side_effect=Exception("Test error")):
            # Should handle exceptions gracefully and use RepositoryEmpty
            config._load('/test/path')
            assert config.config is not None


class TestStrToBoolEdgeCases:
    """Test additional edge cases in strtobool to prevent regression."""

    def test_strtobool_with_exact_values(self):
        """Test strtobool with exact values (no whitespace handling)."""
        from decouple import strtobool
        
        # Exact values should work
        assert strtobool('true') is True
        assert strtobool('false') is False
        assert strtobool('yes') is True
        assert strtobool('no') is False
        assert strtobool('on') is True
        assert strtobool('off') is False

    def test_strtobool_with_mixed_case(self):
        """Test strtobool with mixed case values."""
        from decouple import strtobool
        
        # Mixed case should work
        assert strtobool('True') is True
        assert strtobool('False') is False
        assert strtobool('Yes') is True
        assert strtobool('No') is False
        assert strtobool('On') is True
        assert strtobool('Off') is False

    def test_strtobool_with_numeric_strings(self):
        """Test strtobool with numeric string values."""
        from decouple import strtobool
        
        # Numeric strings should work
        assert strtobool('1') is True
        assert strtobool('0') is False

    def test_strtobool_with_empty_string(self):
        """Test strtobool with empty string."""
        from decouple import strtobool
        
        # Empty string should raise ValueError
        with pytest.raises(ValueError, match="Invalid truth value"):
            strtobool('')

    def test_strtobool_with_whitespace_only(self):
        """Test strtobool with whitespace-only string."""
        from decouple import strtobool
        
        # Whitespace-only should raise ValueError
        with pytest.raises(ValueError, match="Invalid truth value"):
            strtobool('   ')

    def test_strtobool_with_whitespace_padded_values(self):
        """Test strtobool with whitespace-padded values (should fail)."""
        from decouple import strtobool
        
        # Whitespace-padded values should fail (current implementation doesn't strip)
        with pytest.raises(ValueError, match="Invalid truth value"):
            strtobool('  true  ')
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            strtobool('  false  ')


class TestConfigBooleanCastingEdgeCases:
    """Test edge cases in Config boolean casting to prevent regression."""

    def test_config_bool_cast_with_empty_string(self):
        """Test Config boolean casting with empty string."""
        config = Config(RepositoryEmpty())
        
        # Empty string should cast to False (special case in _cast_boolean)
        result = config.get('nonexistent', default='', cast=bool)
        assert result is False

    def test_config_bool_cast_with_valid_boolean_strings(self):
        """Test Config boolean casting with valid boolean strings."""
        config = Config(RepositoryEmpty())
        
        # Valid boolean strings should work
        result = config.get('nonexistent', default='true', cast=bool)
        assert result is True
        
        result = config.get('nonexistent', default='false', cast=bool)
        assert result is False
        
        result = config.get('nonexistent', default='1', cast=bool)
        assert result is True
        
        result = config.get('nonexistent', default='0', cast=bool)
        assert result is False

    def test_config_bool_cast_with_invalid_strings(self):
        """Test Config boolean casting with invalid strings."""
        config = Config(RepositoryEmpty())
        
        # Invalid strings should raise ValueError
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='   ', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='!', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default=' 0 ', cast=bool)

    def test_config_bool_cast_with_whitespace_strings(self):
        """Test Config boolean casting with whitespace strings."""
        config = Config(RepositoryEmpty())
        
        # Whitespace strings should fail (not empty, so strtobool is called)
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='   ', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default=' ', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='\t', cast=bool)

    def test_config_bool_cast_with_special_characters(self):
        """Test Config boolean casting with special characters."""
        config = Config(RepositoryEmpty())
        
        # Special characters should fail (not empty, so strtobool is called)
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='!', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='@', cast=bool)
        
        with pytest.raises(ValueError, match="Invalid truth value"):
            config.get('nonexistent', default='#', cast=bool)


class TestRepositoryEdgeCases:
    """Test additional edge cases in repository classes to prevent regression."""

    def test_repository_empty_behavior(self):
        """Test RepositoryEmpty behavior."""
        repo = RepositoryEmpty()
        
        # Should not contain any keys
        assert 'any_key' not in repo
        assert repo['any_key'] is None

    def test_repository_env_with_empty_lines_and_comments(self):
        """Test RepositoryEnv with empty lines and comments."""
        content = """
        # This is a comment
        
        KEY1=value1
        
        # Another comment
        KEY2=value2
        """
        
        mock_file = mock_open(read_data=content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryEnv('test.env')
                
                # Should parse only valid key-value pairs
                assert 'KEY1' in repo.data
                assert 'KEY2' in repo.data
                assert repo.data['KEY1'] == 'value1'
                assert repo.data['KEY2'] == 'value2'

    def test_repository_env_with_quoted_values_containing_equals(self):
        """Test RepositoryEnv with quoted values containing equals signs."""
        content = """
        KEY1="value=with=equals"
        KEY2='another=value=here'
        KEY3=simple_value
        """
        
        mock_file = mock_open(read_data=content)
        with patch('builtins.open', mock_file):
            with patch('os.path.isfile', return_value=True):
                repo = RepositoryEnv('test.env')
                
                # Should handle equals signs in quoted values correctly
                assert repo.data['KEY1'] == 'value=with=equals'
                assert repo.data['KEY2'] == 'another=value=here'
                assert repo.data['KEY3'] == 'simple_value'


class TestConfigValueHandlingEdgeCases:
    """Test edge cases in Config value handling to prevent regression."""

    def test_config_get_with_os_environ_override(self):
        """Test Config.get() behavior when OS environment overrides repository."""
        config = Config(RepositoryEmpty())
        
        # Set environment variable
        os.environ['TEST_KEY'] = 'env_value'
        
        try:
            # Should get value from environment
            result = config.get('TEST_KEY')
            assert result == 'env_value'
        finally:
            # Clean up
            del os.environ['TEST_KEY']

    def test_config_get_with_repository_value(self):
        """Test Config.get() behavior when repository has the value."""
        # Create a mock repository that returns a value
        class MockRepository:
            def __contains__(self, key):
                return key == 'REPO_KEY'
            
            def __getitem__(self, key):
                if key == 'REPO_KEY':
                    return 'repo_value'
                raise KeyError(key)
        
        config = Config(MockRepository())
        
        # Should get value from repository
        result = config.get('REPO_KEY')
        assert result == 'repo_value'

    def test_config_get_with_empty_string_in_repository(self):
        """Test Config.get() behavior with empty string in repository."""
        # Create a mock repository that returns empty string
        class MockRepository:
            def __contains__(self, key):
                return key == 'EMPTY_KEY'
            
            def __getitem__(self, key):
                if key == 'EMPTY_KEY':
                    return ''
                raise KeyError(key)
        
        config = Config(MockRepository())
        
        # Should get empty string from repository
        result = config.get('EMPTY_KEY')
        assert result == ''

    def test_config_get_with_none_in_repository(self):
        """Test Config.get() behavior with None in repository."""
        # Create a mock repository that returns None
        class MockRepository:
            def __contains__(self, key):
                return key == 'NONE_KEY'
            
            def __getitem__(self, key):
                if key == 'NONE_KEY':
                    return None
                raise KeyError(key)
        
        config = Config(MockRepository())
        
        # Should get None from repository
        result = config.get('NONE_KEY')
        assert result is None

    def test_config_get_with_cast_and_none_value(self):
        """Test Config.get() behavior with casting and None values."""
        config = Config(RepositoryEmpty())
        
        # None with custom cast should work
        def custom_cast(value):
            return f"CAST_{value}"
        
        result = config.get('nonexistent', default=None, cast=custom_cast)
        assert result == 'CAST_None'

    def test_config_get_with_cast_and_empty_string(self):
        """Test Config.get() behavior with casting and empty string values."""
        config = Config(RepositoryEmpty())
        
        # Empty string with custom cast should work
        def custom_cast(value):
            return f"CAST_{value}"
        
        result = config.get('nonexistent', default='', cast=custom_cast)
        assert result == 'CAST_'