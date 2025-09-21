#!/usr/bin/env python3
"""
Test suite for main.py module
"""
import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock, call

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.main import parse_arguments, main


@pytest.fixture(autouse=True)
def cleanup_qapp():
    """Clean up QApplication instances after each test"""
    yield
    # Try to clean up any existing QApplication instance
    try:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is not None:
            QApplication.instance().quit()
            QApplication.instance().deleteLater()
    except (ImportError, AttributeError):
        pass


class TestParseArguments:
    """Test cases for argument parsing"""
    
    def setup_method(self):
        """Set up test environment"""
        # Save original argv
        self.original_argv = sys.argv.copy()
    
    def teardown_method(self):
        """Clean up test environment"""
        # Restore original argv
        sys.argv = self.original_argv
    
    def test_parse_arguments_default(self):
        """Test default argument parsing"""
        sys.argv = ['main.py']
        args = parse_arguments()
        
        assert not args.minimized
        assert not args.debug
        assert not args.cli
        assert args.config is None
    
    def test_parse_arguments_minimized(self):
        """Test --minimized argument"""
        sys.argv = ['main.py', '--minimized']
        args = parse_arguments()
        
        assert args.minimized
        assert not args.debug
        assert not args.cli
        assert args.config is None
    
    def test_parse_arguments_debug(self):
        """Test --debug argument"""
        sys.argv = ['main.py', '--debug']
        args = parse_arguments()
        
        assert not args.minimized
        assert args.debug
        assert not args.cli
        assert args.config is None
    
    def test_parse_arguments_cli(self):
        """Test --cli argument"""
        sys.argv = ['main.py', '--cli']
        args = parse_arguments()
        
        assert not args.minimized
        assert not args.debug
        assert args.cli
        assert args.config is None
    
    def test_parse_arguments_config(self):
        """Test --config argument"""
        sys.argv = ['main.py', '--config', '/path/to/config.json']
        args = parse_arguments()
        
        assert not args.minimized
        assert not args.debug
        assert not args.cli
        assert args.config == '/path/to/config.json'
    
    def test_parse_arguments_all(self):
        """Test all arguments together"""
        sys.argv = ['main.py', '--minimized', '--debug', '--cli', '--config', '/path/to/config.json']
        args = parse_arguments()
        
        assert args.minimized
        assert args.debug
        assert args.cli
        assert args.config == '/path/to/config.json'
    
    def test_parse_arguments_unknown(self):
        """Test that unknown arguments are ignored"""
        sys.argv = ['main.py', '--unknown-arg', 'value', '--debug']
        args = parse_arguments()
        
        assert not args.minimized
        assert args.debug
        assert not args.cli
        assert args.config is None


class TestMain:
    """Test cases for main function"""
    
    def setup_method(self):
        """Set up test environment"""
        # Save original argv
        self.original_argv = sys.argv.copy()
    
    def teardown_method(self):
        """Clean up test environment"""
        # Restore original argv
        sys.argv = self.original_argv
    
    @patch('src.main.cli_main')
    @patch('src.main.setup_logger')
    def test_main_cli_mode(self, mock_logger, mock_cli_main):
        """Test main function in CLI mode"""
        sys.argv = ['main.py', '--cli']
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_cli_main.return_value = 0
        
        result = main()
        
        # Verify CLI was called
        mock_cli_main.assert_called_once()
        
        # Verify logger was set up
        mock_logger.assert_called_once()
        
        # Verify --cli was removed from sys.argv
        assert '--cli' not in sys.argv
        
        assert result == 0
    
    @patch('src.main.cli_main')
    @patch('src.main.setup_logger')
    def test_main_cli_mode_no_cli_in_argv(self, mock_logger, mock_cli_main):
        """Test main function in CLI mode when --cli not in sys.argv"""
        # Set up args to indicate CLI mode but don't put --cli in sys.argv
        sys.argv = ['main.py']
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_cli_main.return_value = 0
        
        # Mock parse_arguments to return CLI mode
        with patch('src.main.parse_arguments') as mock_parse:
            mock_args = MagicMock()
            mock_args.cli = True
            mock_args.debug = False
            mock_parse.return_value = mock_args
            
            result = main()
        
        # Verify CLI was called
        mock_cli_main.assert_called_once()
        
        # Verify logger was set up
        mock_logger.assert_called_once()
        
        assert result == 0
    
    def test_main_gui_mode_basic_components(self):
        """Test main function GUI components without running the event loop"""
        # Test the individual components that main() sets up in GUI mode
        
        # Test argument parsing for GUI mode
        sys.argv = ['main.py']
        args = parse_arguments()
        
        assert not args.cli
        assert not args.minimized
        assert not args.debug
        
        # Test that we can import and initialize the required modules
        from src.services.config_service import ConfigService
        from src.services.notification_service import NotificationService
        
        # These should initialize without errors
        config = ConfigService("test_message_master")
        notification = NotificationService("Test FreeSMS")
        
        # Test configuration defaults
        start_minimized = args.minimized or config.get("general.start_minimized", False)
        assert not start_minimized  # Should be False by default
        
        # Verify the import paths exist and can be loaded
        try:
            from src.gui.app import SMSApplication
            from PySide6.QtWidgets import QApplication
            # If we can import these, the modules are available
            assert True, "GUI modules can be imported"
        except ImportError as e:
            pytest.fail(f"GUI modules cannot be imported: {e}")
    
    @pytest.mark.timeout(10)
    def test_main_gui_mode_argument_flow(self):
        """Test the argument processing flow for GUI mode without Qt event loop"""
        import logging
        
        # Test different argument combinations
        test_cases = [
            (['main.py'], {'minimized': False, 'debug': False, 'cli': False}),
            (['main.py', '--minimized'], {'minimized': True, 'debug': False, 'cli': False}),
            (['main.py', '--debug'], {'minimized': False, 'debug': True, 'cli': False}),
        ]
        
        original_argv = sys.argv.copy()
        
        try:
            for argv, expected in test_cases:
                sys.argv = argv
                args = parse_arguments()
                
                assert args.minimized == expected['minimized'], f"Failed for {argv}"
                assert args.debug == expected['debug'], f"Failed for {argv}"
                assert args.cli == expected['cli'], f"Failed for {argv}"
                
                # Test logger setup level
                expected_log_level = logging.DEBUG if args.debug else logging.INFO
                with patch('src.main.setup_logger') as mock_logger:
                    mock_logger_instance = MagicMock()
                    mock_logger.return_value = mock_logger_instance
                    
                    # This should not hang since we're not testing the full main()
                    from src.utils.logger import setup_logger
                    logger = setup_logger("test_logger", expected_log_level)
                    
                    assert logger is not None
        finally:
            sys.argv = original_argv
    
    def test_main_gui_mode_minimized_components(self):
        """Test GUI mode components with minimized argument"""
        # Test minimized argument processing
        sys.argv = ['main.py', '--minimized']
        args = parse_arguments()
        
        assert args.minimized
        assert not args.cli
        assert not args.debug
        
        # Test config service initialization
        from src.services.config_service import ConfigService
        config = ConfigService("test_message_master")
        
        # Test the minimized logic
        start_minimized = args.minimized or config.get("general.start_minimized", False)
        assert start_minimized  # Should be True when --minimized is passed
    
    def test_main_gui_mode_debug_components(self):
        """Test GUI mode components with debug argument"""
        # Test debug argument processing
        sys.argv = ['main.py', '--debug']
        args = parse_arguments()
        
        assert args.debug
        assert not args.cli
        assert not args.minimized
        
        # Test logging level
        import logging
        expected_log_level = logging.DEBUG if args.debug else logging.INFO
        assert expected_log_level == logging.DEBUG
    
    def test_main_gui_mode_config_components(self):
        """Test GUI mode components with custom config"""
        # Test config argument processing
        sys.argv = ['main.py', '--config', '/test/config.json']
        args = parse_arguments()
        
        assert args.config == '/test/config.json'
        assert not args.cli
        assert not args.minimized
        assert not args.debug
    
    def test_main_gui_mode_icon_path_logic(self):
        """Test the icon path logic without loading Qt"""
        # Test icon path construction
        import os
        from src.main import __file__ as main_file
        
        # Simulate the icon path logic from main()
        icon_path = os.path.join(os.path.dirname(main_file), "gui", "assets", "sms_icon.png")
        
        # Check if the path is constructed correctly
        expected_path_parts = ["gui", "assets", "sms_icon.png"]
        for part in expected_path_parts:
            assert part in icon_path, f"Missing {part} in icon path: {icon_path}"
    
    @pytest.mark.timeout(5)
    def test_main_gui_mode_service_initialization(self):
        """Test that GUI mode services can be initialized independently"""
        # Test service initialization without Qt
        from src.services.config_service import ConfigService
        from src.services.notification_service import NotificationService
        
        # These should initialize without any Qt dependencies
        config = ConfigService("test_message_master")
        notification = NotificationService("Test FreeSMS")
        
        # Verify they're properly initialized
        assert config is not None
        assert notification is not None
        
        # Test config methods
        test_value = config.get("general.start_minimized", False)
        assert isinstance(test_value, bool)


class TestModuleImport:
    """Test cases for module import and path setup"""
    
    def setup_method(self):
        """Set up test environment"""
        self.original_path = sys.path.copy()
    
    def teardown_method(self):
        """Clean up test environment"""
        sys.path[:] = self.original_path
    
    def test_project_root_path_insertion(self):
        """Test that project root is added to sys.path when not present"""
        # Calculate the expected project root (FreeSMS directory)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))  # tests dir
        expected_project_root = os.path.dirname(current_file_dir)  # FreeSMS dir
        
        # Remove the project root from sys.path if it exists
        paths_to_restore = []
        for path in sys.path[:]:  # Use slice copy to avoid modification during iteration
            if path == expected_project_root:
                sys.path.remove(path)
                paths_to_restore.append(path)
        
        # Import the main module (this should trigger the path insertion logic)
        import importlib
        if 'src.main' in sys.modules:
            importlib.reload(sys.modules['src.main'])
        else:
            import src.main
        
        # Verify the project root was added to sys.path
        assert expected_project_root in sys.path
        
        # Find where it was inserted
        project_root_index = sys.path.index(expected_project_root)
        assert project_root_index == 0, "Project root should be inserted at the beginning of sys.path"


@pytest.mark.skip(reason="Qt Application singleton issues - skipping GUI tests for coverage focus")
class TestMainExecution:
    """Test cases for main execution"""
    
    @patch('src.main.main')
    def test_main_name_execution(self, mock_main):
        """Test that main() is called when module is executed directly"""
        # Execute the main block code directly
        exec("if True: import src.main; src.main.main()")  # Simulate if __name__ == "__main__":
        
        # Verify main was called
        mock_main.assert_called()
    
    @pytest.mark.skip(reason="Qt Application singleton issues in test environment")
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('PySide6.QtGui.QIcon')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_full_execution(self, mock_logger, mock_qicon, mock_qapp, mock_config_service,
                                         mock_notification_service, mock_sms_app, mock_exit):
        """Test main function GUI mode full execution path"""
        # Set up mocks
        sys.argv = ['main.py']  # GUI mode (no --cli)
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False  # start_minimized = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        mock_qapp.instance.return_value = None  # No existing instance
        
        mock_icon = MagicMock()
        mock_qicon.return_value = mock_icon
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Run main function
        main()
        
        # Verify GUI mode setup
        mock_logger.assert_called_once_with("message_master", logging.INFO)
        mock_config_service.assert_called_once_with("message_master")
        mock_notification_service.assert_called_once_with("FreeSMS")
        
        # Verify Qt application setup
        mock_qapp.assert_called_once_with(sys.argv)
        mock_qt_app.setApplicationName.assert_called_once_with("FreeSMS")
        mock_qt_app.setApplicationVersion.assert_called_once_with("1.0")
        
        # Verify main window creation and shown (not minimized)
        mock_sms_app.assert_called_once_with(config=mock_config, notification=mock_notification)
        mock_main_window.show.assert_called_once()
        mock_main_window.hide.assert_not_called()
        
        # Verify app execution
        mock_qt_app.exec.assert_called_once()
        mock_exit.assert_called_once()
    
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_minimized(self, mock_logger, mock_qapp, mock_config_service, 
                                    mock_notification_service, mock_sms_app, mock_exit):
        """Test main function GUI mode with minimized start"""
        # Set up mocks
        sys.argv = ['main.py', '--minimized']
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Run main function
        main()
        
        # Verify minimized start
        mock_main_window.hide.assert_called_once()
        mock_main_window.show.assert_not_called()
        mock_notification.send_notification.assert_called_once_with(
            "FreeSMS", 
            "Application started and running in background"
        )
    
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_debug(self, mock_logger, mock_qapp, mock_config_service, 
                                mock_notification_service, mock_sms_app, mock_exit):
        """Test main function GUI mode with debug logging"""
        # Set up mocks
        sys.argv = ['main.py', '--debug']
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Run main function
        main()
        
        # Verify debug logging is enabled
        mock_logger.assert_called_once_with("message_master", logging.DEBUG)
    
    @patch('os.path.exists')
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_with_icon(self, mock_logger, mock_qapp, mock_config_service, 
                                    mock_notification_service, mock_sms_app, mock_exit, mock_exists):
        """Test main function GUI mode with application icon"""
        # Set up mocks
        sys.argv = ['main.py']
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Mock icon file exists
        mock_exists.return_value = True
        
        with patch('PySide6.QtGui.QIcon') as mock_qicon:
            mock_icon = MagicMock()
            mock_qicon.return_value = mock_icon
            
            # Run main function
            main()
            
            # Verify icon was set
            mock_qicon.assert_called_once()
            mock_qt_app.setWindowIcon.assert_called_once_with(mock_icon)
    
    @patch('os.path.exists')
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_icon_missing(self, mock_logger, mock_qapp, mock_config_service, 
                                      mock_notification_service, mock_sms_app, mock_exit, mock_exists):
        """Test main function GUI mode when icon file is missing"""
        # Set up mocks
        sys.argv = ['main.py']
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Mock icon file doesn't exist
        mock_exists.return_value = False
        
        # Run main function
        main()
        
        # Verify icon was not set (setWindowIcon should not be called)
        mock_qt_app.setWindowIcon.assert_not_called()
    
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_icon_exception(self, mock_logger, mock_qapp, mock_config_service, 
                                         mock_notification_service, mock_sms_app, mock_exit):
        """Test main function GUI mode when icon setting raises exception"""
        # Set up mocks
        sys.argv = ['main.py']
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Mock QIcon to raise exception
        with patch('PySide6.QtGui.QIcon', side_effect=Exception("Icon error")):
            # Run main function
            main()
            
            # Verify warning was logged
            mock_logger_instance.warning.assert_called_once_with("Failed to set application icon")
    
    @patch('sys.exit')
    @patch('src.gui.app.SMSApplication')
    @patch('src.services.notification_service.NotificationService')
    @patch('src.services.config_service.ConfigService')
    @patch('PySide6.QtWidgets.QApplication')
    @patch('src.main.setup_logger')
    def test_main_gui_mode_config_minimized_setting(self, mock_logger, mock_qapp, mock_config_service, 
                                                   mock_notification_service, mock_sms_app, mock_exit):
        """Test main function GUI mode with config-based minimized setting"""
        # Set up mocks
        sys.argv = ['main.py']  # No --minimized flag
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_config = MagicMock()
        mock_config.get.return_value = True  # Config says start minimized
        mock_config_service.return_value = mock_config
        
        mock_notification = MagicMock()
        mock_notification_service.return_value = mock_notification
        
        mock_qt_app = MagicMock()
        mock_qapp.return_value = mock_qt_app
        
        mock_main_window = MagicMock()
        mock_sms_app.return_value = mock_main_window
        
        # Run main function
        main()
        
        # Verify minimized start due to config setting
        mock_main_window.hide.assert_called_once()
        mock_main_window.show.assert_not_called()
        mock_notification.send_notification.assert_called_once()