"""Tests for REPL functionality."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
import threading
import time
from contextlib import contextmanager
from rich.panel import Panel
from rich.markdown import Markdown

from src.repl import SocratesREPL
from src.agent import Conversation
from src.providers.base import ChatMessage, ChatResponse


class TestREPL(unittest.TestCase):
    """Test REPL functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".socrates"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create a test config
        test_config = {
            "default_provider": "glm",
            "providers": {
                "glm": {
                    "api_key": "test_api_key_12345678",
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "default_model": "glm-4.5"
                }
            }
        }

        config_file = self.config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f)

    def test_repl_initialization(self):
        """Test REPL initialization."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session:
                mock_session.return_value = Mock()

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")
                    self.assertIsNotNone(repl)
                    self.assertEqual(repl.provider_name, "glm")
                    self.assertFalse(repl.stream)

    def test_repl_initialization_with_stream_enabled(self):
        """Test REPL can start with stream mode enabled."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session:
                mock_session.return_value = Mock()

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm", stream=True)
                    self.assertTrue(repl.stream)

    def test_startup_header_contains_logo_and_metadata(self):
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm")

                    with patch('src.repl.core.Path.cwd', return_value=Path(self.temp_dir)):
                        # Capture stdout to verify fallback path output
                        import io
                        from contextlib import redirect_stdout

                        f = io.StringIO()
                        with redirect_stdout(f):
                            repl._print_startup_header()

                        rendered = f.getvalue()
                        self.assertIn("Socrates", rendered)
                        self.assertIn("glm-4.5", rendered)
                        self.assertIn("GLM Provider", rendered)
                        # Path may be truncated, just check start and end parts
                        self.assertTrue(
                            self.temp_dir[:20] in rendered or self.temp_dir[-20:] in rendered
                        )

    def test_handle_command_exit(self):
        """Test /exit command."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")

                    with self.assertRaises(SystemExit):
                        repl.handle_command("/exit")

    def test_handle_command_clear(self):
        """Test /clear command."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session:
                mock_session_instance = Mock()
                mock_session_instance.conversation = Mock()
                mock_session.return_value = mock_session_instance

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")
                    repl.handle_command("/clear")

                    self.assertEqual(len(repl.session.conversation.messages), 0)

    def test_handle_command_stream_toggle(self):
        """Test /stream command toggles stream mode safely."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")
                    self.assertFalse(repl.stream)

                    repl.handle_command("/stream on")
                    self.assertTrue(repl.stream)

                    repl.handle_command("/stream off")
                    self.assertFalse(repl.stream)

    def test_handle_command_render_last_renders_markdown(self):
        """Test /render-last re-renders the last assistant response."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session_factory:
                mock_session = Mock()
                mock_session.conversation = Conversation()
                mock_session.conversation.add_assistant_message("## Hello\n\n- item")
                mock_session_factory.return_value = mock_session

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")
                    repl.session.conversation.add_assistant_message("## Hello\n\n- item")
                    repl.console.print = Mock()
                    repl.handle_command("/render-last")

                    self.assertTrue(any(
                        args and isinstance(args[0], Markdown)
                        for args, _kwargs in repl.console.print.call_args_list
                    ))

    def test_handle_command_render_last_without_message(self):
        """Test /render-last handles empty history gracefully."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session_factory:
                mock_session = Mock()
                mock_session.conversation = Conversation()
                mock_session_factory.return_value = mock_session

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider

                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()
                    repl.handle_command("/render-last")

                    self.assertTrue(any(
                        args and "No assistant response available to render." in str(args[0])
                        for args, _kwargs in repl.console.print.call_args_list
                    ))

    def test_chat_uses_true_api_stream_for_simple_prompt(self):
        """Simple prompts should use provider.chat_stream when stream mode is enabled."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session_factory:
                mock_session = Mock()
                mock_session.conversation = Conversation()
                mock_session_factory.return_value = mock_session

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider.chat_stream.return_value = iter(["hel", "lo"])
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm", stream=True)
                    repl.console.print = Mock()

                    repl.chat("hello there")

                    mock_provider.chat_stream.assert_called_once()
                    self.assertFalse(any(
                        args and isinstance(args[0], Markdown)
                        for args, _kwargs in repl.console.print.call_args_list
                    ))
                    self.assertEqual(len(repl.session.conversation.messages), 2)
                    self.assertEqual(repl.session.conversation.messages[1].role, "assistant")
                    last_content = repl.session.conversation.messages[1].content
                    if isinstance(last_content, list):
                        self.assertEqual(last_content[0].text, "hello")
                    else:
                        self.assertEqual(last_content, "hello")

    def test_chat_uses_query_engine_for_code_task(self):
        """Code-like prompts use the new QueryEngine path."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session_factory:
                mock_session = Mock()
                mock_session.conversation = Conversation()
                mock_session_factory.return_value = mock_session

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider.chat_stream_response.side_effect = NotImplementedError()
                    mock_provider.chat.return_value = ChatResponse(
                        content="Done reading README.",
                        model="test",
                        usage={"input_tokens": 10, "output_tokens": 5},
                        finish_reason="end_turn",
                        tool_uses=None,
                    )
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm", stream=True)
                    repl.console.print = Mock()
                    repl.chat("please inspect README.md")

                    mock_provider.chat.assert_called()

    def test_chat_uses_query_engine_on_stream_init_failure(self):
        """If real streaming fails, fall back to QueryEngine."""
        with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
            with patch('src.repl.core.SessionStorage') as mock_session_factory:
                mock_session = Mock()
                mock_session.conversation = Conversation()
                mock_session_factory.return_value = mock_session

                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider.chat_stream.side_effect = RuntimeError("stream unavailable")
                    mock_provider.chat_stream_response.side_effect = NotImplementedError()
                    mock_provider.chat.return_value = ChatResponse(
                        content="fallback response",
                        model="test",
                        usage={"input_tokens": 10, "output_tokens": 5},
                        finish_reason="end_turn",
                        tool_uses=None,
                    )
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm", stream=True)
                    repl.console.print = Mock()
                    repl.chat("hello there")

                    mock_provider.chat_stream.assert_called_once()
                    mock_provider.chat.assert_called()

    def test_handle_command_slash_shows_commands_and_skills(self):
        skills_dir = Path(self.temp_dir) / "skills"
        (skills_dir / "hello").mkdir(parents=True, exist_ok=True)
        (skills_dir / "hello" / "SKILL.md").write_text(
            "---\n"
            "description: say hello\n"
            "---\n"
            "Hello\n",
            encoding="utf-8",
        )
        with patch.dict("os.environ", {"SOCRATES_SKILLS_DIR": str(skills_dir)}):
            with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
                with patch('src.repl.core.SessionStorage'):
                    with patch('src.providers.get_provider_class') as mock_provider_class:
                        mock_provider = Mock()
                        mock_provider.model = "glm-4.5"
                        mock_provider_class.return_value = mock_provider

                        repl = SocratesREPL(provider_name="glm")
                        repl.console.print = Mock()
                        repl.handle_command("/")
                        rendered = "\n".join(
                            str(args[0]) for args, _kwargs in repl.console.print.call_args_list if args
                        )
                        self.assertIn("Available commands and skills", rendered)
                        self.assertIn("/hello", rendered)

    def test_handle_command_slash_prefix_filters(self):
        skills_dir = Path(self.temp_dir) / "skills"
        (skills_dir / "hello").mkdir(parents=True, exist_ok=True)
        (skills_dir / "hello" / "SKILL.md").write_text(
            "---\n"
            "description: say hello\n"
            "---\n"
            "Hello\n",
            encoding="utf-8",
        )
        with patch.dict("os.environ", {"SOCRATES_SKILLS_DIR": str(skills_dir)}):
            with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
                with patch('src.repl.core.SessionStorage'):
                    with patch('src.providers.get_provider_class') as mock_provider_class:
                        mock_provider = Mock()
                        mock_provider.model = "glm-4.5"
                        mock_provider_class.return_value = mock_provider

                        repl = SocratesREPL(provider_name="glm")
                        repl.console.print = Mock()
                        repl.handle_command("/he")
                        rendered = "\n".join(
                            str(args[0]) for args, _kwargs in repl.console.print.call_args_list if args
                        )
                        self.assertIn("/help", rendered)
                        self.assertIn("/hello", rendered)

    def test_handle_command_skill_invokes_skill_tool_and_chats_with_prompt(self):
        skills_dir = Path(self.temp_dir) / "skills"
        (skills_dir / "hello").mkdir(parents=True, exist_ok=True)
        (skills_dir / "hello" / "SKILL.md").write_text(
            "---\n"
            "description: say hello\n"
            "arguments: [name]\n"
            "---\n"
            "Hello $name\n",
            encoding="utf-8",
        )
        with patch.dict("os.environ", {"SOCRATES_SKILLS_DIR": str(skills_dir)}):
            with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
                with patch('src.repl.core.SessionStorage'):
                    with patch('src.providers.get_provider_class') as mock_provider_class:
                        mock_provider = Mock()
                        mock_provider.model = "glm-4.5"
                        mock_provider_class.return_value = mock_provider

                        repl = SocratesREPL(provider_name="glm")
                        repl.chat = Mock()
                        repl.handle_command("/hello bob")
                        args, _kwargs = repl.chat.call_args
                        self.assertIn("Hello bob", args[0])

    def test_load_session(self):
        """Test session loading from SessionStorage."""
        from src.services.session_storage import SessionStorage
        from src.types.messages import create_user_message

        with tempfile.TemporaryDirectory() as td:
            sessions_dir = Path(td)
            storage = SessionStorage(session_id="loaded_session_123", sessions_dir=sessions_dir)
            storage.init_metadata(model="glm-4.5", cwd=str(Path.cwd()), title="Loaded")
            storage.write_message(create_user_message("hello"))
            storage.flush()

            with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
                with patch('src.providers.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm", sessions_dir=sessions_dir)
                    repl.load_session("loaded_session_123")

                    self.assertEqual(repl.session.session_id, "loaded_session_123")
                    self.assertEqual(len(repl._engine_messages), 1)

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        with tempfile.TemporaryDirectory() as td:
            with patch('src.config.get_config_path', return_value=self.config_dir / "config.json"):
                with patch('src.providers.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = Mock(return_value=mock_provider)

                    repl = SocratesREPL(provider_name="glm", sessions_dir=Path(td))
                    original_session = repl.session

                    repl.load_session("nonexistent")

                    # Session should not change
                    self.assertEqual(repl.session, original_session)

    def test_permission_prompt_is_serialized(self):
        """Concurrent permission checks should not open overlapping prompts."""
        with patch('src.repl.core.get_provider_config', return_value={
            "api_key": "test_api_key_12345678",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4.5",
        }), patch('src.repl.core.PromptSession') as mock_prompt_session:
            mock_prompt_session.return_value = Mock(prompt=Mock(return_value=""))
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider
                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()

                    in_prompt = 0
                    max_in_prompt = 0
                    counter_lock = threading.Lock()

                    def fake_input(_prompt: str) -> str:
                        nonlocal in_prompt, max_in_prompt
                        with counter_lock:
                            in_prompt += 1
                            if in_prompt > max_in_prompt:
                                max_in_prompt = in_prompt
                        time.sleep(0.03)
                        with counter_lock:
                            in_prompt -= 1
                        return "1"

                    repl._safe_input = fake_input  # type: ignore[assignment]

                    t1 = threading.Thread(
                        target=repl._handle_permission_request,
                        args=("Grep", "Claude wants to use Grep. Allow?", None),
                    )
                    t2 = threading.Thread(
                        target=repl._handle_permission_request,
                        args=("Read", "Claude wants to use Read. Allow?", None),
                    )
                    t1.start()
                    t2.start()
                    t1.join()
                    t2.join()

                    self.assertEqual(max_in_prompt, 1)

    def test_permission_prompt_cached_per_tool(self):
        """After first decision, same tool should not prompt again."""
        with patch('src.repl.core.get_provider_config', return_value={
            "api_key": "test_api_key_12345678",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4.5",
        }), patch('src.repl.core.PromptSession') as mock_prompt_session:
            mock_prompt_session.return_value = Mock(prompt=Mock(return_value=""))
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider
                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()

                    prompt_calls = 0

                    def fake_input(_prompt: str) -> str:
                        nonlocal prompt_calls
                        prompt_calls += 1
                        return "1"

                    repl._safe_input = fake_input  # type: ignore[assignment]

                    first = repl._handle_permission_request(
                        "Grep",
                        "Claude wants to use Grep. Allow?",
                        None,
                    )
                    second = repl._handle_permission_request(
                        "Grep",
                        "Claude wants to use Grep. Allow?",
                        None,
                    )

                    self.assertEqual(first, (True, False))
                    self.assertEqual(second, (True, False))
                    self.assertEqual(prompt_calls, 1)

    def test_permission_prompt_uses_choice_box(self):
        """Permission requests should use the compact choice box selector."""
        with patch('src.repl.core.get_provider_config', return_value={
            "api_key": "test_api_key_12345678",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4.5",
        }), patch('src.repl.core.PromptSession') as mock_prompt_session:
            mock_prompt_session.return_value = Mock(prompt=Mock(return_value=""))
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider
                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()
                    repl._safe_input = Mock(side_effect=AssertionError("text prompt should not be used"))
                    repl._select_permission_choice = Mock(return_value=True)

                    result = repl._handle_permission_request(
                        "Grep",
                        "Claude wants to use Grep. Allow?",
                        None,
                    )

                    self.assertEqual(result, (True, False))
                    repl._select_permission_choice.assert_called_once()

    def test_permission_choice_state_moves_between_allow_and_deny(self):
        """Left/right arrows should toggle Allow once and Deny."""
        from src.repl.core import PermissionChoiceState

        state = PermissionChoiceState()
        self.assertEqual(state.selected_label, "Allow once")

        state.move_right()
        self.assertEqual(state.selected_label, "Deny")

        state.move_left()
        self.assertEqual(state.selected_label, "Allow once")

    def test_permission_prompt_pauses_live_status_while_rendering_selector(self):
        """Permission UI should own the terminal while live status is mounted."""
        with patch('src.repl.core.get_provider_config', return_value={
            "api_key": "test_api_key_12345678",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4.5",
        }), patch('src.repl.core.PromptSession') as mock_prompt_session:
            mock_prompt_session.return_value = Mock(prompt=Mock(return_value=""))
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider
                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()

                    events: list[str] = []

                    class FakeLiveStatus:
                        @contextmanager
                        def paused(self):
                            events.append("pause-enter")
                            try:
                                yield
                            finally:
                                events.append("pause-exit")

                    def fake_select() -> bool:
                        events.append("select")
                        return True

                    repl._active_live_status = FakeLiveStatus()  # type: ignore[assignment]
                    repl._select_permission_choice = fake_select  # type: ignore[assignment]

                    result = repl._handle_permission_request(
                        "Grep",
                        "Claude wants to use Grep. Allow?",
                        None,
                    )

                    self.assertEqual(result, (True, False))
                    self.assertEqual(events, ["pause-enter", "select", "pause-exit"])

    def test_permission_prompt_renders_message_as_single_panel(self):
        """Permission details should render as one stable Rich block."""
        with patch('src.repl.core.get_provider_config', return_value={
            "api_key": "test_api_key_12345678",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4.5",
        }), patch('src.repl.core.PromptSession') as mock_prompt_session:
            mock_prompt_session.return_value = Mock(prompt=Mock(return_value=""))
            with patch('src.repl.core.SessionStorage'):
                with patch('src.repl.core.get_provider_class') as mock_provider_class:
                    mock_provider = Mock()
                    mock_provider.model = "glm-4.5"
                    mock_provider_class.return_value = mock_provider
                    repl = SocratesREPL(provider_name="glm")
                    repl.console.print = Mock()
                    repl._select_permission_choice = Mock(return_value=True)

                    repl._handle_permission_request(
                        "Grep",
                        "Claude wants to use Grep. Allow?",
                        None,
                    )

                    printed = [args[0] for args, _kwargs in repl.console.print.call_args_list if args]
                    self.assertTrue(any(isinstance(item, Panel) for item in printed))


class TestConversation(unittest.TestCase):
    """Test conversation management."""

    def test_add_message(self):
        """Test adding messages to conversation."""
        conv = Conversation()
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")

        self.assertEqual(len(conv.messages), 2)
        self.assertEqual(conv.messages[0].role, "user")
        self.assertEqual(conv.messages[0].content, "Hello")
        self.assertEqual(conv.messages[1].role, "assistant")

    def test_max_history(self):
        """Test max history limit."""
        conv = Conversation(max_history=3)

        # Add 5 messages
        for i in range(5):
            conv.add_message("user", f"Message {i}")

        # Should only keep last 3
        self.assertEqual(len(conv.messages), 3)
        self.assertEqual(conv.messages[0].content, "Message 2")
        self.assertEqual(conv.messages[2].content, "Message 4")

    def test_get_messages(self):
        """Test getting messages in API format."""
        conv = Conversation()
        conv.add_message("user", "Test")
        conv.add_message("assistant", "Response")

        messages = conv.get_messages()

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], {"role": "user", "content": "Test"})
        self.assertEqual(messages[1]["role"], "assistant")
        content = messages[1]["content"]
        if isinstance(content, list):
            self.assertEqual(content[0]["text"], "Response")
        else:
            self.assertEqual(content, "Response")

    def test_clear(self):
        """Test clearing conversation."""
        conv = Conversation()
        conv.add_message("user", "Test")
        conv.clear()

        self.assertEqual(len(conv.messages), 0)

    def test_serialization(self):
        """Test conversation serialization."""
        conv = Conversation()
        conv.add_message("user", "Test")
        conv.add_message("assistant", "Response")

        # Serialize
        data = conv.to_dict()
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 2)

        # Deserialize
        conv2 = Conversation.from_dict(data)
        self.assertEqual(len(conv2.messages), 2)
        self.assertEqual(conv2.messages[0].content, "Test")


if __name__ == '__main__':
    unittest.main()
