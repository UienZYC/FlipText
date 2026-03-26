from __future__ import annotations

import copy
import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config_store import (
    DEFAULT_SYSTEM_PROMPT,
    ensure_config,
    get_config_path,
    make_id,
    save_config,
    set_active_profile,
    set_engine,
)


class SettingsApp:
    def __init__(self) -> None:
        self.script_dir = Path(__file__).resolve().parent
        self.config = ensure_config(self.script_dir)
        self.config_path = get_config_path()
        self.show_key = False
        self.dirty = False
        self.current_selection_id = ""

        self.root = tk.Tk()
        self.root.title("FlipText Settings")
        self.root.geometry("1120x720")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.engine_var = tk.StringVar(value=self.config["translation"]["engine"])
        self.provider_name_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.model_name_var = tk.StringVar()
        self.model_enabled_var = tk.BooleanVar(value=True)
        self.timeout_var = tk.StringVar(value="30000")
        self.status_var = tk.StringVar(value=f"Config: {self.config_path}")

        self.tree: ttk.Treeview
        self.system_prompt_text: tk.Text
        self.provider_section: ttk.LabelFrame
        self.model_section: ttk.LabelFrame

        self._build_ui()
        self._refresh_tree()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(4, weight=1)

        ttk.Label(top, text="Translation engine").grid(row=0, column=0, sticky="w")
        engine_combo = ttk.Combobox(
            top,
            textvariable=self.engine_var,
            values=["edge", "llm"],
            state="readonly",
            width=12,
        )
        engine_combo.grid(row=0, column=1, padx=(8, 16), sticky="w")
        engine_combo.bind("<<ComboboxSelected>>", lambda _event: self._save_engine_immediately())

        ttk.Button(top, text="Save Settings", command=self._save_all_changes).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(top, text="Open Config Folder", command=self._open_config_folder).grid(row=0, column=3, sticky="w")

        main = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        self._build_tree_panel(main)
        self._build_detail_panel(main)

        status = ttk.Label(self.root, textvariable=self.status_var, padding=(10, 0, 10, 10))
        status.grid(row=2, column=0, sticky="ew")

        self.root.bind("<Control-s>", lambda _event: self._save_all_changes())

    def _build_tree_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Providers And Models", padding=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, show="tree", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_tree_selected())

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Add Provider", command=self._add_provider).grid(row=0, column=0, sticky="ew")
        ttk.Button(buttons, text="Add Model", command=self._add_model).grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ttk.Button(buttons, text="Delete Selected", command=self._delete_selected).grid(row=0, column=2, padx=(8, 0), sticky="ew")
        ttk.Button(buttons, text="Set Active Model", command=self._set_active_model).grid(row=0, column=3, padx=(8, 0), sticky="ew")

    def _build_detail_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        self.provider_section = ttk.LabelFrame(frame, text="Provider", padding=10)
        self.provider_section.grid(row=0, column=0, sticky="ew")
        self.provider_section.columnconfigure(1, weight=1)

        ttk.Label(self.provider_section, text="Provider name").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.provider_section, textvariable=self.provider_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(self.provider_section, text="Base URL").grid(row=1, column=0, sticky="w")
        ttk.Entry(self.provider_section, textvariable=self.base_url_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(self.provider_section, text="API key").grid(row=2, column=0, sticky="w")
        key_entry = ttk.Entry(self.provider_section, textvariable=self.api_key_var, show="*")
        key_entry.grid(row=2, column=1, sticky="ew")
        ttk.Button(self.provider_section, text="Show/Hide", command=lambda: self._toggle_key_visibility(key_entry)).grid(row=2, column=2, padx=(8, 0))

        self.model_section = ttk.LabelFrame(frame, text="Model", padding=10)
        self.model_section.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.model_section.columnconfigure(1, weight=1)
        self.model_section.rowconfigure(4, weight=1)

        ttk.Label(self.model_section, text="Model name").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.model_section, textvariable=self.model_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(self.model_section, text="Timeout (ms)").grid(row=1, column=0, sticky="w")
        ttk.Entry(self.model_section, textvariable=self.timeout_var).grid(row=1, column=1, sticky="ew", pady=(0, 6))

        ttk.Checkbutton(self.model_section, text="Enabled", variable=self.model_enabled_var).grid(row=2, column=1, sticky="w", pady=(0, 6))

        ttk.Label(self.model_section, text="System prompt").grid(row=3, column=0, sticky="nw")
        self.system_prompt_text = tk.Text(self.model_section, height=14, wrap="word")
        self.system_prompt_text.grid(row=4, column=0, columnspan=3, sticky="nsew")

        hint = ttk.Label(
            frame,
            text="Provider and model edits are staged here. Use Save Settings to commit them all.",
        )
        hint.grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _save_engine_immediately(self) -> None:
        set_engine(self.config, self.engine_var.get())
        save_config(self.config)
        self.status_var.set(f"Engine saved immediately. Config: {self.config_path}")

    def _toggle_key_visibility(self, entry: ttk.Entry) -> None:
        self.show_key = not self.show_key
        entry.configure(show="" if self.show_key else "*")

    def _providers(self) -> list[dict]:
        return self.config["providers"]

    def _selected_provider(self) -> dict | None:
        selection = self.current_selection_id
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
        selection = self.current_selection_id
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

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())

        active_provider_id = self.config["translation"].get("active_provider_id", "")
        active_model_id = self.config["translation"].get("active_model_id", "")

        for provider in self._providers():
            provider_iid = self._provider_iid(provider)
            self.tree.insert("", "end", iid=provider_iid, text=provider["name"], open=True)
            for model in provider["models"]:
                label = model["name"]
                if provider["id"] == active_provider_id and model["id"] == active_model_id:
                    label += " [Active]"
                if not model.get("enabled", True):
                    label += " [Disabled]"
                self.tree.insert(provider_iid, "end", iid=self._model_iid(provider, model), text=label)

        if self.current_selection_id and self.tree.exists(self.current_selection_id):
            self.tree.selection_set(self.current_selection_id)
            self.tree.focus(self.current_selection_id)
        elif self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self.current_selection_id = first

        self._load_selection_into_form()

    def _load_selection_into_form(self) -> None:
        provider = self._selected_provider()
        model = self._selected_model()

        if provider is None:
            self._clear_provider_fields()
            self._clear_model_fields()
            return

        self.provider_name_var.set(provider["name"])
        self.base_url_var.set(provider["base_url"])
        self.api_key_var.set(provider["api_key"])

        if model is None:
            self._clear_model_fields()
        else:
            self.model_name_var.set(model["name"])
            self.timeout_var.set(str(model["timeout_ms"]))
            self.model_enabled_var.set(bool(model.get("enabled", True)))
            self.system_prompt_text.delete("1.0", tk.END)
            self.system_prompt_text.insert("1.0", model.get("system_prompt", DEFAULT_SYSTEM_PROMPT))

    def _clear_provider_fields(self) -> None:
        self.provider_name_var.set("")
        self.base_url_var.set("")
        self.api_key_var.set("")

    def _clear_model_fields(self) -> None:
        self.model_name_var.set("")
        self.timeout_var.set("30000")
        self.model_enabled_var.set(True)
        self.system_prompt_text.delete("1.0", tk.END)
        self.system_prompt_text.insert("1.0", DEFAULT_SYSTEM_PROMPT)

    def _commit_current_form_to_draft(self) -> bool:
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
            model["system_prompt"] = self.system_prompt_text.get("1.0", tk.END).strip() or DEFAULT_SYSTEM_PROMPT
        return True

    def _mark_dirty(self, message: str = "Unsaved changes.") -> None:
        self.dirty = True
        self.status_var.set(f"{message} Config: {self.config_path}")

    def _on_tree_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        if self.current_selection_id and self.current_selection_id != selection[0]:
            if not self._commit_current_form_to_draft():
                if self.tree.exists(self.current_selection_id):
                    self.tree.selection_set(self.current_selection_id)
                return
        self.current_selection_id = selection[0]
        self._load_selection_into_form()

    def _add_provider(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        provider = {
            "id": make_id("provider"),
            "name": f"Provider {len(self._providers()) + 1}",
            "base_url": "",
            "api_key": "",
            "models": [],
        }
        self._providers().append(provider)
        self.current_selection_id = self._provider_iid(provider)
        self._mark_dirty("Provider added.")
        self._refresh_tree()

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
        }
        provider["models"].append(model)
        self.current_selection_id = self._model_iid(provider, model)
        self._mark_dirty("Model added.")
        self._refresh_tree()

    def _delete_selected(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        provider = self._selected_provider()
        model = self._selected_model()

        if model is not None and provider is not None:
            if not messagebox.askyesno("Delete Model", f"Delete model '{model['name']}'?"):
                return
            provider["models"] = [item for item in provider["models"] if item["id"] != model["id"]]
            self.current_selection_id = self._provider_iid(provider)
            self._mark_dirty("Model deleted.")
            self._refresh_tree()
            return

        if provider is not None:
            if not messagebox.askyesno("Delete Provider", f"Delete provider '{provider['name']}'?"):
                return
            self.config["providers"] = [item for item in self._providers() if item["id"] != provider["id"]]
            self.current_selection_id = ""
            self._mark_dirty("Provider deleted.")
            self._refresh_tree()

    def _set_active_model(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        provider = self._selected_provider()
        model = self._selected_model()
        if provider is None or model is None:
            messagebox.showinfo("Set Active Model", "Please select a model under a provider.")
            return
        set_active_profile(self.config, f"{provider['id']}::{model['id']}")
        self._mark_dirty("Active model changed.")
        self._refresh_tree()

    def _save_all_changes(self) -> None:
        if not self._commit_current_form_to_draft():
            return
        save_config(self.config)
        self.dirty = False
        self.status_var.set(f"Settings saved. Config: {self.config_path}")
        self._refresh_tree()

    def _open_config_folder(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(self.config_path.parent)

    def _on_close(self) -> None:
        if not self.dirty:
            self.root.destroy()
            return

        choice = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved provider/model changes.\n\nYes: save and close\nNo: discard and close\nCancel: stay here",
        )
        if choice is None:
            return
        if choice:
            self._save_all_changes()
        self.root.destroy()

    def _provider_iid(self, provider: dict) -> str:
        return f"provider:{provider['id']}"

    def _model_iid(self, provider: dict, model: dict) -> str:
        return f"model:{provider['id']}::{model['id']}"

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SettingsApp().run()
