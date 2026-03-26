from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config_store import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
    ensure_config,
    format_shortcut_label,
    get_config_path,
    make_id,
    normalize_behavior_type,
    normalize_shortcut,
    save_config,
    set_active_profile,
)


class SettingsApp:
    def __init__(self) -> None:
        self.script_dir = Path(__file__).resolve().parent
        self.config = ensure_config(self.script_dir)
        self.config_path = get_config_path()
        self.current_model_selection = ""
        self.current_prompt_id = ""
        self.current_behavior_id = ""
        self.current_binding_id = ""
        self.show_key = False
        self.dirty = False

        self.root = tk.Tk()
        self.root.title("FlipText Settings")
        self.root.geometry("1240x860")
        self.root.minsize(1080, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value=f"Config: {self.config_path}")
        self.engine_var = tk.StringVar(value=self.config["translation"]["engine"])
        self.provider_name_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.model_name_var = tk.StringVar()
        self.model_enabled_var = tk.BooleanVar(value=True)
        self.timeout_var = tk.StringVar(value="30000")
        self.prompt_name_var = tk.StringVar()
        self.behavior_name_var = tk.StringVar()
        self.behavior_type_var = tk.StringVar(value="llm_prompt")
        self.behavior_profile_var = tk.StringVar()
        self.behavior_prompt_var = tk.StringVar()
        self.binding_shortcut_var = tk.StringVar()
        self.binding_behavior_var = tk.StringVar()

        self._build_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        self.models_tab = ttk.Frame(notebook, padding=10)
        self.prompts_tab = ttk.Frame(notebook, padding=10)
        self.behaviors_tab = ttk.Frame(notebook, padding=10)
        self.bindings_tab = ttk.Frame(notebook, padding=10)

        notebook.add(self.models_tab, text="Models")
        notebook.add(self.prompts_tab, text="Prompts")
        notebook.add(self.behaviors_tab, text="Behaviors")
        notebook.add(self.bindings_tab, text="Bindings")

        self._build_models_tab(self.models_tab)
        self._build_prompts_tab(self.prompts_tab)
        self._build_behaviors_tab(self.behaviors_tab)
        self._build_bindings_tab(self.bindings_tab)

        status = ttk.Label(self.root, textvariable=self.status_var, padding=(10, 8, 10, 6))
        status.grid(row=1, column=0, sticky="ew")

        footer = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Button(footer, text="Open Config Folder", command=self._open_config_folder).grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Save Settings", command=self._save_all_changes).grid(row=0, column=1, sticky="e")

        self.root.bind("<Control-s>", lambda _event: self._save_all_changes())

    def _build_models_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(parent, text="Providers And Models", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_tree_selected())

        buttons = ttk.Frame(left)
        buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        buttons.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Button(buttons, text="Add Provider", command=self._add_provider).grid(row=0, column=0, sticky="ew")
        ttk.Button(buttons, text="Add Model", command=self._add_model).grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ttk.Button(buttons, text="Delete Selected", command=self._delete_selected).grid(row=0, column=2, padx=(8, 0), sticky="ew")
        ttk.Button(buttons, text="Set Active Model", command=self._set_active_model).grid(row=0, column=3, padx=(8, 0), sticky="ew")

        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        action_box = ttk.LabelFrame(right, text="Actions", padding=10)
        action_box.grid(row=0, column=0, sticky="ew")
        ttk.Label(action_box, text="Default engine").grid(row=0, column=0, sticky="w")
        ttk.Combobox(action_box, textvariable=self.engine_var, values=["edge", "llm"], state="readonly", width=10).grid(
            row=0, column=1, padx=(8, 0), sticky="w"
        )

        details = ttk.Frame(right)
        details.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        details.columnconfigure(0, weight=1)
        details.rowconfigure(1, weight=1)

        provider_box = ttk.LabelFrame(details, text="Provider", padding=10)
        provider_box.grid(row=0, column=0, sticky="ew")
        provider_box.columnconfigure(1, weight=1)
        ttk.Label(provider_box, text="Provider name").grid(row=0, column=0, sticky="w")
        ttk.Entry(provider_box, textvariable=self.provider_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(provider_box, text="Base URL").grid(row=1, column=0, sticky="w")
        ttk.Entry(provider_box, textvariable=self.base_url_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(provider_box, text="API key").grid(row=2, column=0, sticky="w")
        key_entry = ttk.Entry(provider_box, textvariable=self.api_key_var, show="*")
        key_entry.grid(row=2, column=1, sticky="ew")
        ttk.Button(provider_box, text="Show/Hide", command=lambda: self._toggle_key_visibility(key_entry)).grid(row=2, column=2, padx=(8, 0))

        model_box = ttk.LabelFrame(details, text="Model", padding=10)
        model_box.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        model_box.columnconfigure(1, weight=1)
        model_box.rowconfigure(4, weight=3)
        model_box.rowconfigure(6, weight=2)
        ttk.Label(model_box, text="Model name").grid(row=0, column=0, sticky="w")
        ttk.Entry(model_box, textvariable=self.model_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(model_box, text="Timeout (ms)").grid(row=1, column=0, sticky="w")
        ttk.Entry(model_box, textvariable=self.timeout_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(model_box, text="Enabled", variable=self.model_enabled_var).grid(row=2, column=1, sticky="w", pady=(0, 6))
        ttk.Label(model_box, text="Legacy system prompt").grid(row=3, column=0, sticky="nw")
        self.system_prompt_text = tk.Text(model_box, height=8, wrap="word")
        self.system_prompt_text.grid(row=4, column=0, columnspan=3, sticky="nsew")
        ttk.Label(model_box, text="Legacy user prompt template").grid(row=5, column=0, sticky="nw", pady=(8, 0))
        self.user_prompt_template_text = tk.Text(model_box, height=6, wrap="word")
        self.user_prompt_template_text.grid(row=6, column=0, columnspan=3, sticky="nsew")
        ttk.Label(model_box, text="Placeholders: {text}, {source_lang}, {target_lang}.").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            model_box,
            text="If text contains Chinese characters: zh -> en. Otherwise: en -> zh.",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _build_prompts_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(parent, text="Prompt Library", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.prompt_list = tk.Listbox(left, exportselection=False)
        self.prompt_list.grid(row=0, column=0, sticky="nsew")
        self.prompt_list.bind("<<ListboxSelect>>", lambda _event: self._on_prompt_selected())
        prompt_buttons = ttk.Frame(left)
        prompt_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        prompt_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(prompt_buttons, text="Add Prompt", command=self._add_prompt).grid(row=0, column=0, sticky="ew")
        ttk.Button(prompt_buttons, text="Delete Prompt", command=self._delete_prompt).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        right = ttk.LabelFrame(parent, text="Prompt Editor", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        right.rowconfigure(2, weight=2)
        right.rowconfigure(4, weight=2)
        ttk.Label(right, text="Prompt name").grid(row=0, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.prompt_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(right, text="System prompt").grid(row=1, column=0, sticky="nw")
        self.prompt_system_text = tk.Text(right, height=10, wrap="word")
        self.prompt_system_text.grid(row=2, column=0, columnspan=2, sticky="nsew")
        ttk.Label(right, text="User prompt").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        self.prompt_user_text = tk.Text(right, height=10, wrap="word")
        self.prompt_user_text.grid(row=4, column=0, columnspan=2, sticky="nsew")

    def _build_behaviors_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(parent, text="Behavior Library", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.behavior_list = tk.Listbox(left, exportselection=False)
        self.behavior_list.grid(row=0, column=0, sticky="nsew")
        self.behavior_list.bind("<<ListboxSelect>>", lambda _event: self._on_behavior_selected())
        behavior_buttons = ttk.Frame(left)
        behavior_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        behavior_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(behavior_buttons, text="Add Behavior", command=self._add_behavior).grid(row=0, column=0, sticky="ew")
        ttk.Button(behavior_buttons, text="Delete Behavior", command=self._delete_behavior).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        right = ttk.LabelFrame(parent, text="Behavior Editor", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        ttk.Label(right, text="Behavior name").grid(row=0, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.behavior_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(right, text="Behavior type").grid(row=1, column=0, sticky="w")
        combo = ttk.Combobox(
            right,
            textvariable=self.behavior_type_var,
            values=["llm_prompt", "edge_translate", "show_shortcuts"],
            state="readonly",
        )
        combo.grid(row=1, column=1, sticky="w", pady=(0, 6))
        combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_behavior_field_state())
        ttk.Label(right, text="Model").grid(row=2, column=0, sticky="w")
        self.behavior_profile_combo = ttk.Combobox(right, textvariable=self.behavior_profile_var, state="readonly")
        self.behavior_profile_combo.grid(row=2, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(right, text="Prompt").grid(row=3, column=0, sticky="w")
        self.behavior_prompt_combo = ttk.Combobox(right, textvariable=self.behavior_prompt_var, state="readonly")
        self.behavior_prompt_combo.grid(row=3, column=1, sticky="ew", pady=(0, 6))

    def _build_bindings_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(parent, text="Shortcut Bindings", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.binding_list = tk.Listbox(left, exportselection=False)
        self.binding_list.grid(row=0, column=0, sticky="nsew")
        self.binding_list.bind("<<ListboxSelect>>", lambda _event: self._on_binding_selected())
        binding_buttons = ttk.Frame(left)
        binding_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        binding_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(binding_buttons, text="Add Binding", command=self._add_binding).grid(row=0, column=0, sticky="ew")
        ttk.Button(binding_buttons, text="Delete Binding", command=self._delete_binding).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        right = ttk.LabelFrame(parent, text="Binding Editor", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        ttk.Label(right, text="Shortcut").grid(row=0, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.binding_shortcut_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(right, text="Behavior").grid(row=1, column=0, sticky="w")
        self.binding_behavior_combo = ttk.Combobox(right, textvariable=self.binding_behavior_var, state="readonly")
        self.binding_behavior_combo.grid(row=1, column=1, sticky="ew", pady=(0, 6))

    def _providers(self) -> list[dict]:
        return self.config["providers"]

    def _prompts(self) -> list[dict]:
        return self.config["prompt_library"]

    def _behaviors(self) -> list[dict]:
        return self.config["behavior_library"]

    def _bindings(self) -> list[dict]:
        return self.config["shortcut_bindings"]

    def _build_profile_options(self) -> dict[str, str]:
        options: dict[str, str] = {}
        for provider in self._providers():
            for model in provider["models"]:
                options[f"{provider['name']} / {model['name']}"] = f"{provider['id']}::{model['id']}"
        return options

    def _build_prompt_options(self) -> dict[str, str]:
        return {prompt["name"]: prompt["id"] for prompt in self._prompts()}

    def _build_behavior_options(self) -> dict[str, str]:
        return {behavior["name"]: behavior["id"] for behavior in self._behaviors()}

    def _selected_provider(self) -> dict | None:
        selection = self.current_model_selection
        if not selection:
            return None
        if selection.startswith("provider:"):
            provider_id = selection.split(":", 1)[1]
        elif selection.startswith("model:"):
            provider_id = selection.split(":", 1)[1].split("::", 1)[0]
        else:
            return None
        for provider in self._providers():
            if provider["id"] == provider_id:
                return provider
        return None

    def _selected_model(self) -> dict | None:
        selection = self.current_model_selection
        if not selection.startswith("model:"):
            return None
        provider_id, model_id = selection.split(":", 1)[1].split("::", 1)
        for provider in self._providers():
            if provider["id"] != provider_id:
                continue
            for model in provider["models"]:
                if model["id"] == model_id:
                    return model
        return None

    def _selected_prompt(self) -> dict | None:
        for prompt in self._prompts():
            if prompt["id"] == self.current_prompt_id:
                return prompt
        return None

    def _selected_behavior(self) -> dict | None:
        for behavior in self._behaviors():
            if behavior["id"] == self.current_behavior_id:
                return behavior
        return None

    def _selected_binding(self) -> dict | None:
        for binding in self._bindings():
            if binding["id"] == self.current_binding_id:
                return binding
        return None

    def _restore_list_selection(self, widget: tk.Listbox, ids: list[str], attr_name: str) -> None:
        current = getattr(self, attr_name)
        if current and current in ids:
            index = ids.index(current)
            widget.selection_clear(0, tk.END)
            widget.selection_set(index)
            widget.activate(index)
        elif ids:
            setattr(self, attr_name, ids[0])
            widget.selection_set(0)
            widget.activate(0)
        else:
            setattr(self, attr_name, "")

    def _label_for_value(self, options: dict[str, str], value: str) -> str:
        for label, current in options.items():
            if current == value:
                return label
        return ""

    def _value_for_label(self, options: dict[str, str], label: str) -> str:
        return options.get(label, "")

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def _text_value(self, widget: tk.Text) -> str:
        return widget.get("1.0", tk.END).strip()

    def _toggle_key_visibility(self, entry: ttk.Entry) -> None:
        self.show_key = not self.show_key
        entry.configure(show="" if self.show_key else "*")

    def _refresh_all(self) -> None:
        self._refresh_tree()
        self._refresh_prompt_list()
        self._refresh_behavior_list()
        self._refresh_binding_list()
        self._refresh_behavior_combo_options()
        self._refresh_binding_combo_options()

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        active_provider_id = self.config["translation"].get("active_provider_id", "")
        active_model_id = self.config["translation"].get("active_model_id", "")
        for provider in self._providers():
            provider_iid = f"provider:{provider['id']}"
            self.tree.insert("", "end", iid=provider_iid, text=provider["name"], open=True)
            for model in provider["models"]:
                label = model["name"]
                if provider["id"] == active_provider_id and model["id"] == active_model_id:
                    label += " [Active]"
                if not model.get("enabled", True):
                    label += " [Disabled]"
                self.tree.insert(provider_iid, "end", iid=f"model:{provider['id']}::{model['id']}", text=label)
        if self.current_model_selection and self.tree.exists(self.current_model_selection):
            self.tree.selection_set(self.current_model_selection)
            self.tree.focus(self.current_model_selection)
        elif self.tree.get_children():
            self.current_model_selection = self.tree.get_children()[0]
            self.tree.selection_set(self.current_model_selection)
            self.tree.focus(self.current_model_selection)
        self._load_model_selection()

    def _refresh_prompt_list(self) -> None:
        self.prompt_list.delete(0, tk.END)
        ids: list[str] = []
        for prompt in self._prompts():
            self.prompt_list.insert(tk.END, prompt["name"])
            ids.append(prompt["id"])
        self._restore_list_selection(self.prompt_list, ids, "current_prompt_id")
        self._load_prompt_selection()

    def _refresh_behavior_list(self) -> None:
        self.behavior_list.delete(0, tk.END)
        ids: list[str] = []
        for behavior in self._behaviors():
            self.behavior_list.insert(tk.END, behavior["name"])
            ids.append(behavior["id"])
        self._restore_list_selection(self.behavior_list, ids, "current_behavior_id")
        self._load_behavior_selection()

    def _refresh_binding_list(self) -> None:
        self.binding_list.delete(0, tk.END)
        ids: list[str] = []
        behavior_map = {behavior["id"]: behavior["name"] for behavior in self._behaviors()}
        for binding in self._bindings():
            self.binding_list.insert(tk.END, f"{format_shortcut_label(binding['shortcut'])} -> {behavior_map.get(binding['behavior_id'], 'Unknown')}")
            ids.append(binding["id"])
        self._restore_list_selection(self.binding_list, ids, "current_binding_id")
        self._load_binding_selection()

    def _load_model_selection(self) -> None:
        provider = self._selected_provider()
        model = self._selected_model()
        if provider is None:
            self.provider_name_var.set("")
            self.base_url_var.set("")
            self.api_key_var.set("")
            self.model_name_var.set("")
            self.timeout_var.set("30000")
            self.model_enabled_var.set(True)
            self._set_text(self.system_prompt_text, DEFAULT_SYSTEM_PROMPT)
            self._set_text(self.user_prompt_template_text, DEFAULT_USER_PROMPT_TEMPLATE)
            return
        self.provider_name_var.set(provider["name"])
        self.base_url_var.set(provider["base_url"])
        self.api_key_var.set(provider["api_key"])
        if model is None:
            self.model_name_var.set("")
            self.timeout_var.set("30000")
            self.model_enabled_var.set(True)
            self._set_text(self.system_prompt_text, DEFAULT_SYSTEM_PROMPT)
            self._set_text(self.user_prompt_template_text, DEFAULT_USER_PROMPT_TEMPLATE)
            return
        self.model_name_var.set(model["name"])
        self.timeout_var.set(str(model["timeout_ms"]))
        self.model_enabled_var.set(bool(model.get("enabled", True)))
        self._set_text(self.system_prompt_text, model.get("system_prompt", DEFAULT_SYSTEM_PROMPT))
        self._set_text(self.user_prompt_template_text, model.get("user_prompt_template", DEFAULT_USER_PROMPT_TEMPLATE))

    def _load_prompt_selection(self) -> None:
        prompt = self._selected_prompt()
        if prompt is None:
            self.prompt_name_var.set("")
            self._set_text(self.prompt_system_text, "")
            self._set_text(self.prompt_user_text, "{text}")
            return
        self.prompt_name_var.set(prompt["name"])
        self._set_text(self.prompt_system_text, prompt["system_prompt"])
        self._set_text(self.prompt_user_text, prompt["user_prompt"])

    def _load_behavior_selection(self) -> None:
        profile_options = self._build_profile_options()
        prompt_options = self._build_prompt_options()
        behavior = self._selected_behavior()
        if behavior is None:
            self.behavior_name_var.set("")
            self.behavior_type_var.set("llm_prompt")
            self.behavior_profile_var.set("")
            self.behavior_prompt_var.set("")
            self._sync_behavior_field_state()
            return
        self.behavior_name_var.set(behavior["name"])
        self.behavior_type_var.set(behavior["type"])
        self.behavior_profile_var.set(self._label_for_value(profile_options, behavior["profile_id"]))
        self.behavior_prompt_var.set(self._label_for_value(prompt_options, behavior["prompt_id"]))
        self._sync_behavior_field_state()

    def _load_binding_selection(self) -> None:
        options = self._build_behavior_options()
        binding = self._selected_binding()
        if binding is None:
            self.binding_shortcut_var.set("")
            self.binding_behavior_var.set("")
            return
        self.binding_shortcut_var.set(binding["shortcut"])
        self.binding_behavior_var.set(self._label_for_value(options, binding["behavior_id"]))

    def _refresh_behavior_combo_options(self) -> None:
        self.behavior_profile_combo.configure(values=list(self._build_profile_options().keys()))
        self.behavior_prompt_combo.configure(values=list(self._build_prompt_options().keys()))

    def _refresh_binding_combo_options(self) -> None:
        self.binding_behavior_combo.configure(values=list(self._build_behavior_options().keys()))

    def _commit_current_form_to_draft(self) -> bool:
        self.config["translation"]["engine"] = self.engine_var.get()

        provider = self._selected_provider()
        if provider is not None:
            provider["name"] = self.provider_name_var.get().strip() or provider["name"]
            provider["base_url"] = self.base_url_var.get().strip()
            provider["api_key"] = self.api_key_var.get().strip()

        model = self._selected_model()
        if model is not None:
            timeout_text = self.timeout_var.get().strip()
            if not timeout_text.isdigit() or int(timeout_text) < 1000:
                messagebox.showerror("Invalid Timeout", "Timeout must be an integer >= 1000 ms.")
                return False
            model["name"] = self.model_name_var.get().strip() or model["name"]
            model["enabled"] = bool(self.model_enabled_var.get())
            model["timeout_ms"] = int(timeout_text)
            model["system_prompt"] = self._text_value(self.system_prompt_text) or DEFAULT_SYSTEM_PROMPT
            model["user_prompt_template"] = self._text_value(self.user_prompt_template_text) or DEFAULT_USER_PROMPT_TEMPLATE

        prompt = self._selected_prompt()
        if prompt is not None:
            prompt["name"] = self.prompt_name_var.get().strip() or prompt["name"]
            prompt["system_prompt"] = self._text_value(self.prompt_system_text)
            prompt["user_prompt"] = self._text_value(self.prompt_user_text) or "{text}"

        behavior = self._selected_behavior()
        if behavior is not None:
            behavior_type = normalize_behavior_type(self.behavior_type_var.get())
            behavior["name"] = self.behavior_name_var.get().strip() or behavior["name"]
            behavior["type"] = behavior_type
            behavior["profile_id"] = self._value_for_label(self._build_profile_options(), self.behavior_profile_var.get())
            behavior["prompt_id"] = self._value_for_label(self._build_prompt_options(), self.behavior_prompt_var.get())
            if behavior_type != "llm_prompt":
                behavior["profile_id"] = ""
                behavior["prompt_id"] = ""
            if behavior_type == "llm_prompt" and (not behavior["profile_id"] or not behavior["prompt_id"]):
                messagebox.showerror("Incomplete Behavior", "LLM behaviors require both a model and a prompt.")
                return False

        binding = self._selected_binding()
        if binding is not None:
            shortcut = normalize_shortcut(self.binding_shortcut_var.get())
            if not shortcut:
                messagebox.showerror("Invalid Shortcut", "Use shortcuts like F1, F1+1, or F1+Q.")
                return False
            behavior_id = self._value_for_label(self._build_behavior_options(), self.binding_behavior_var.get())
            if not behavior_id:
                messagebox.showerror("Missing Behavior", "Please choose a behavior for the binding.")
                return False
            for other in self._bindings():
                if other["id"] != binding["id"] and other["shortcut"] == shortcut:
                    messagebox.showerror("Duplicate Shortcut", f"Shortcut '{shortcut}' is already bound.")
                    return False
            binding["shortcut"] = shortcut
            binding["behavior_id"] = behavior_id

        return True

    def _sync_behavior_field_state(self) -> None:
        state = "readonly" if normalize_behavior_type(self.behavior_type_var.get()) == "llm_prompt" else "disabled"
        self.behavior_profile_combo.configure(state=state)
        self.behavior_prompt_combo.configure(state=state)

    def _mark_dirty(self, message: str) -> None:
        self.dirty = True
        self.status_var.set(f"{message} Config: {self.config_path}")

    def _on_tree_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        if self.current_model_selection and self.current_model_selection != selection[0] and not self._commit_current_form_to_draft():
            if self.tree.exists(self.current_model_selection):
                self.tree.selection_set(self.current_model_selection)
            return
        self.current_model_selection = selection[0]
        self._load_model_selection()

    def _on_prompt_selected(self) -> None:
        selection = self.prompt_list.curselection()
        if not selection:
            return
        new_id = self._prompts()[selection[0]]["id"]
        if self.current_prompt_id and self.current_prompt_id != new_id and not self._commit_current_form_to_draft():
            self._refresh_prompt_list()
            return
        self.current_prompt_id = new_id
        self._load_prompt_selection()

    def _on_behavior_selected(self) -> None:
        selection = self.behavior_list.curselection()
        if not selection:
            return
        new_id = self._behaviors()[selection[0]]["id"]
        if self.current_behavior_id and self.current_behavior_id != new_id and not self._commit_current_form_to_draft():
            self._refresh_behavior_list()
            return
        self.current_behavior_id = new_id
        self._load_behavior_selection()

    def _on_binding_selected(self) -> None:
        selection = self.binding_list.curselection()
        if not selection:
            return
        new_id = self._bindings()[selection[0]]["id"]
        if self.current_binding_id and self.current_binding_id != new_id and not self._commit_current_form_to_draft():
            self._refresh_binding_list()
            return
        self.current_binding_id = new_id
        self._load_binding_selection()

    def _add_provider(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        provider = {"id": make_id("provider"), "name": f"Provider {len(self._providers()) + 1}", "base_url": "", "api_key": "", "models": []}
        self._providers().append(provider)
        self.current_model_selection = f"provider:{provider['id']}"
        self._mark_dirty("Provider added.")
        self._refresh_all()

    def _add_model(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        provider = self._selected_provider()
        if provider is None:
            messagebox.showinfo("Add Model", "Please select a provider first.")
            return
        model = {
            "id": make_id("model"),
            "name": f"Model {len(provider['models']) + 1}",
            "enabled": True,
            "timeout_ms": 30000,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_prompt_template": DEFAULT_USER_PROMPT_TEMPLATE,
        }
        provider["models"].append(model)
        self.current_model_selection = f"model:{provider['id']}::{model['id']}"
        self._mark_dirty("Model added.")
        self._refresh_all()

    def _delete_selected(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        model = self._selected_model()
        provider = self._selected_provider()
        if model is not None and provider is not None:
            if not messagebox.askyesno("Delete Model", f"Delete model '{model['name']}'?"):
                return
            provider["models"] = [item for item in provider["models"] if item["id"] != model["id"]]
            self.current_model_selection = f"provider:{provider['id']}"
            self._mark_dirty("Model deleted.")
            self._refresh_all()
            return
        if provider is not None:
            if not messagebox.askyesno("Delete Provider", f"Delete provider '{provider['name']}'?"):
                return
            self.config["providers"] = [item for item in self._providers() if item["id"] != provider["id"]]
            self.current_model_selection = ""
            self._mark_dirty("Provider deleted.")
            self._refresh_all()

    def _set_active_model(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        model = self._selected_model()
        provider = self._selected_provider()
        if provider is None or model is None:
            messagebox.showinfo("Set Active Model", "Please select a model under a provider.")
            return
        set_active_profile(self.config, f"{provider['id']}::{model['id']}")
        self._mark_dirty("Active model changed.")
        self._refresh_all()

    def _add_prompt(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        prompt = {"id": make_id("prompt"), "name": f"Prompt {len(self._prompts()) + 1}", "system_prompt": "", "user_prompt": "{text}"}
        self._prompts().append(prompt)
        self.current_prompt_id = prompt["id"]
        self._mark_dirty("Prompt added.")
        self._refresh_all()

    def _delete_prompt(self) -> None:
        prompt = self._selected_prompt()
        if prompt is None:
            messagebox.showinfo("Delete Prompt", "Please select a prompt first.")
            return
        if any(behavior.get("prompt_id", "") == prompt["id"] for behavior in self._behaviors()):
            messagebox.showerror("Delete Prompt", "This prompt is still used by a behavior.")
            return
        if not messagebox.askyesno("Delete Prompt", f"Delete prompt '{prompt['name']}'?"):
            return
        self.config["prompt_library"] = [item for item in self._prompts() if item["id"] != prompt["id"]]
        self.current_prompt_id = ""
        self._mark_dirty("Prompt deleted.")
        self._refresh_all()

    def _add_behavior(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        behavior = {"id": make_id("behavior"), "name": f"Behavior {len(self._behaviors()) + 1}", "type": "llm_prompt", "profile_id": "", "prompt_id": ""}
        self._behaviors().append(behavior)
        self.current_behavior_id = behavior["id"]
        self._mark_dirty("Behavior added.")
        self._refresh_all()

    def _delete_behavior(self) -> None:
        behavior = self._selected_behavior()
        if behavior is None:
            messagebox.showinfo("Delete Behavior", "Please select a behavior first.")
            return
        if behavior["id"] in {"behavior-show-shortcuts", "behavior-edge-translate"}:
            messagebox.showerror("Delete Behavior", "Built-in behaviors cannot be deleted.")
            return
        if any(binding.get("behavior_id", "") == behavior["id"] for binding in self._bindings()):
            messagebox.showerror("Delete Behavior", "This behavior is still used by a shortcut binding.")
            return
        if not messagebox.askyesno("Delete Behavior", f"Delete behavior '{behavior['name']}'?"):
            return
        self.config["behavior_library"] = [item for item in self._behaviors() if item["id"] != behavior["id"]]
        self.current_behavior_id = ""
        self._mark_dirty("Behavior deleted.")
        self._refresh_all()

    def _add_binding(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        first_behavior = self._behaviors()[0]["id"] if self._behaviors() else ""
        binding = {"id": make_id("binding"), "shortcut": "", "behavior_id": first_behavior}
        self._bindings().append(binding)
        self.current_binding_id = binding["id"]
        self._mark_dirty("Binding added.")
        self._refresh_all()

    def _delete_binding(self) -> None:
        binding = self._selected_binding()
        if binding is None:
            messagebox.showinfo("Delete Binding", "Please select a binding first.")
            return
        if not messagebox.askyesno("Delete Binding", f"Delete binding '{format_shortcut_label(binding['shortcut'])}'?"):
            return
        self.config["shortcut_bindings"] = [item for item in self._bindings() if item["id"] != binding["id"]]
        self.current_binding_id = ""
        self._mark_dirty("Binding deleted.")
        self._refresh_all()

    def _save_all_changes(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        save_config(self.config)
        self.dirty = False
        self.status_var.set(f"Settings saved. Config: {self.config_path}")
        self._refresh_all()

    def _open_config_folder(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(self.config_path.parent)

    def _on_close(self) -> None:
        if not self.dirty:
            self.root.destroy()
            return
        choice = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved model, prompt, behavior, or binding changes.\n\nYes: save and close\nNo: discard and close\nCancel: stay here",
        )
        if choice is None:
            return
        if choice:
            self._save_all_changes()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SettingsApp().run()
