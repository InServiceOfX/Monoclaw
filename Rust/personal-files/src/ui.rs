//! Native GTK UI. Directory scans run on a bounded, single background worker.
use crate::{
    appearance,
    core::{self, Entry, Preferences, Sort},
};
use gtk::{gdk, gdk_pixbuf, gio, glib, pango, prelude::*};
use std::{
    cell::{Cell, RefCell},
    path::{Path, PathBuf},
    rc::Rc,
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};

#[derive(Clone)]
struct Request {
    generation: u64,
    target: PathBuf,
    select: Option<PathBuf>,
    record: bool,
    history_index: Option<usize>,
    fallback: bool,
}
struct Scan {
    request: Request,
    result: std::io::Result<Vec<Entry>>,
}
struct Navigation {
    current: PathBuf,
    history: Vec<PathBuf>,
    index: usize,
    generation: u64,
    loading: bool,
    items: Vec<Entry>,
}

pub struct Browser {
    pub window: gtk::ApplicationWindow,
    header: gtk::HeaderBar,
    address: gtk::Entry,
    tree: gtk::TreeView,
    store: gtk::ListStore,
    sidebar: gtk::Box,
    status: gtk::Label,
    empty: gtk::Label,
    pin: gtk::Button,
    back: gtk::Button,
    forward: gtk::Button,
    css: gtk::CssProvider,
    prefs: RefCell<Preferences>,
    nav: RefCell<Navigation>,
    displayed: RefCell<Vec<PathBuf>>,
    columns: Vec<(Sort, gtk::TreeViewColumn)>,
    sender: mpsc::Sender<Request>,
    monitor: RefCell<Option<gio::FileMonitor>>,
    changed: Cell<Option<Instant>>,
    alive: Cell<bool>,
}

fn icon_button(icon: &str, tooltip: &str) -> gtk::Button {
    let button = gtk::Button::from_icon_name(Some(icon), gtk::IconSize::Button);
    button.set_tooltip_text(Some(tooltip));
    button
}

impl Browser {
    pub fn new(app: &gtk::Application, start: Option<PathBuf>, prefs: Preferences) -> Rc<Self> {
        let window = gtk::ApplicationWindow::builder()
            .application(app)
            .title("Personal Files")
            .default_width(1080)
            .default_height(680)
            .build();
        window.set_size_request(700, 380);
        let header = gtk::HeaderBar::builder()
            .title("Personal Files")
            .subtitle("Your places, one click away")
            .show_close_button(true)
            .build();
        header.set_decoration_layout(Some("close,minimize,maximize:"));
        if let Ok(icon) = gdk_pixbuf::Pixbuf::from_read(std::io::Cursor::new(
            include_bytes!("../assets/personal-files.svg").as_slice(),
        )) {
            window.set_icon(Some(&icon));
        }
        window.set_titlebar(Some(&header));
        let back = icon_button("go-previous-symbolic", "Back · Alt+Left");
        let forward = icon_button("go-next-symbolic", "Forward · Alt+Right");
        let up = icon_button("go-up-symbolic", "Parent folder · Alt+Up");
        header.pack_start(&back);
        header.pack_start(&forward);
        header.pack_start(&up);
        let skin = gtk::MenuButton::builder().label("Appearance").build();
        header.pack_end(&skin);
        let root = gtk::Box::new(gtk::Orientation::Vertical, 0);
        window.add(&root);
        let toolbar = gtk::Box::new(gtk::Orientation::Horizontal, 8);
        toolbar.set_widget_name("toolbar");
        let address = gtk::Entry::builder()
            .hexpand(true)
            .placeholder_text("Go to a path — /absolute, ~/home, or relative")
            .build();
        address.set_tooltip_text(Some("Paste a path and press Enter. Relative paths start at the current folder. Ctrl+L to focus."));
        let pin = icon_button("non-starred-symbolic", "Favorite this folder · Ctrl+D");
        let copy = icon_button(
            "edit-copy-symbolic",
            "Copy selected paths, or current folder · Ctrl+C",
        );
        let refresh = icon_button("view-refresh-symbolic", "Refresh · Ctrl+R");
        toolbar.pack_start(&address, true, true, 0);
        for button in [&pin, &copy, &refresh] {
            toolbar.pack_start(button, false, false, 0);
        }
        root.pack_start(&toolbar, false, false, 0);
        let pane = gtk::Paned::new(gtk::Orientation::Horizontal);
        pane.set_position(235);
        root.pack_start(&pane, true, true, 0);
        let sidebar = gtk::Box::new(gtk::Orientation::Vertical, 0);
        sidebar.set_widget_name("sidebar");
        let sidebar_scroll =
            gtk::ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
        sidebar_scroll.set_policy(gtk::PolicyType::Never, gtk::PolicyType::Automatic);
        sidebar_scroll.add(&sidebar);
        pane.pack1(&sidebar_scroll, false, false);
        let canvas = gtk::Overlay::new();
        canvas.set_widget_name("canvas");
        pane.pack2(&canvas, true, false);
        let scroller = gtk::ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
        canvas.add(&scroller);
        let store = gtk::ListStore::new(&[
            String::static_type(),
            String::static_type(),
            String::static_type(),
            String::static_type(),
            String::static_type(),
            u32::static_type(),
        ]);
        let tree = gtk::TreeView::with_model(&store);
        tree.set_search_column(1);
        tree.set_tooltip_column(4);
        tree.selection().set_mode(gtk::SelectionMode::Multiple);
        let name = gtk::TreeViewColumn::new();
        name.set_title("Name");
        name.set_expand(true);
        name.set_min_width(180);
        let icon = gtk::CellRendererPixbuf::new();
        icon.set_property("stock-size", 3u32);
        TreeViewColumnExt::pack_start(&name, &icon, false);
        TreeViewColumnExt::add_attribute(&name, &icon, "icon-name", 0);
        let text = gtk::CellRendererText::new();
        text.set_ellipsize(pango::EllipsizeMode::Middle);
        text.set_ypad(9);
        TreeViewColumnExt::pack_start(&name, &text, true);
        TreeViewColumnExt::add_attribute(&name, &text, "text", 1);
        let mut columns = vec![(Sort::Name, name)];
        for (title, index, key, width) in [
            ("Modified", 2, Sort::Modified, 165),
            ("Size", 3, Sort::Size, 90),
        ] {
            let cell = gtk::CellRendererText::new();
            cell.set_ypad(9);
            let column = gtk::TreeViewColumn::new();
            column.set_title(title);
            TreeViewColumnExt::pack_start(&column, &cell, true);
            TreeViewColumnExt::add_attribute(&column, &cell, "text", index);
            column.set_min_width(width);
            columns.push((key, column));
        }
        for (_, column) in &columns {
            column.set_clickable(true);
            column.set_resizable(true);
            tree.append_column(column);
        }
        scroller.add(&tree);
        let empty = gtk::Label::new(Some("This folder is empty"));
        empty.set_halign(gtk::Align::Center);
        empty.set_valign(gtk::Align::Center);
        empty.set_no_show_all(true);
        canvas.add_overlay(&empty);
        canvas.set_overlay_pass_through(&empty, true);
        let footer = gtk::Box::new(gtk::Orientation::Horizontal, 8);
        footer.set_widget_name("status");
        let status = gtk::Label::builder()
            .xalign(0.)
            .hexpand(true)
            .ellipsize(pango::EllipsizeMode::Middle)
            .build();
        footer.pack_start(&status, true, true, 0);
        let hint = gtk::Label::new(Some(
            "Hidden files visible · Ctrl+L: path · Ctrl+Shift+C: shell path",
        ));
        hint.style_context().add_class("hint");
        footer.pack_end(&hint, false, false, 0);
        root.pack_end(&footer, false, false, 0);
        let css = gtk::CssProvider::new();
        if let Some(screen) = WidgetExt::screen(&window) {
            gtk::StyleContext::add_provider_for_screen(
                &screen,
                &css,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        let (sender, receiver) = mpsc::channel::<Request>();
        let (results, responses) = mpsc::channel::<Scan>();
        thread::spawn(move || {
            while let Ok(mut request) = receiver.recv() {
                // Coalesce pending navigations; at most one scan runs at once.
                while let Ok(newer) = receiver.try_recv() {
                    request = newer;
                }
                let result = core::entries(&request.target);
                if results.send(Scan { request, result }).is_err() {
                    break;
                }
            }
        });
        let start = start.unwrap_or_else(|| prefs.data.last_path.clone());
        let browser = Rc::new(Self {
            window,
            header,
            address,
            tree,
            store,
            sidebar,
            status,
            empty,
            pin,
            back,
            forward,
            css,
            prefs: RefCell::new(prefs),
            nav: RefCell::new(Navigation {
                current: core::home(),
                history: vec![],
                index: 0,
                generation: 0,
                loading: false,
                items: vec![],
            }),
            displayed: RefCell::new(vec![]),
            columns,
            sender,
            monitor: RefCell::new(None),
            changed: Cell::new(None),
            alive: Cell::new(true),
        });
        // Signals use weak references, so closing a window releases its state.
        macro_rules! connect_button {
            ($button:expr, $method:ident) => {{
                let weak = Rc::downgrade(&browser);
                $button.connect_clicked(move |_| {
                    if let Some(b) = weak.upgrade() {
                        b.$method();
                    }
                });
            }};
        }
        connect_button!(browser.pin, toggle_favorite);
        connect_button!(refresh, refresh);
        {
            let weak = Rc::downgrade(&browser);
            copy.connect_clicked(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.copy(false, None);
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            up.connect_clicked(move |_| {
                if let Some(b) = weak.upgrade() {
                    let parent = b.current().parent().unwrap_or(Path::new("/")).to_path_buf();
                    b.navigate(&parent, true, None, false);
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.back.connect_clicked(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.go_history(-1);
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.forward.connect_clicked(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.go_history(1);
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.address.connect_activate(move |entry| {
                if let Some(b) = weak.upgrade() {
                    b.go_text(&entry.text());
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.tree.selection().connect_changed(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.update_status();
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.tree.connect_row_activated(move |_, row, _| {
                if let Some(b) = weak.upgrade() {
                    if let Some(path) = b.row_path(row) {
                        b.open(&path);
                    }
                }
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.tree.connect_button_press_event(move |tree, event| {
                if event.button() != 3 {
                    return glib::Propagation::Proceed;
                }
                if let Some(b) = weak.upgrade() {
                    let (x, y) = event.position();
                    if let Some((Some(row), _, _, _)) = tree.path_at_pos(x as i32, y as i32) {
                        if !tree.selection().path_is_selected(&row) {
                            tree.selection().unselect_all();
                            tree.selection().select_path(&row);
                        }
                    } else {
                        tree.selection().unselect_all();
                    }
                    let mut paths = b.selected();
                    if paths.is_empty() {
                        paths.push(b.current());
                    }
                    b.path_menu(paths).popup_at_pointer(Some(event));
                }
                glib::Propagation::Stop
            });
        }
        for (key, column) in &browser.columns {
            let key = *key;
            let weak = Rc::downgrade(&browser);
            column.connect_clicked(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.sort(key);
                }
            });
        }
        let targets = [
            gtk::TargetEntry::new("text/uri-list", gtk::TargetFlags::OTHER_APP, 0),
            gtk::TargetEntry::new("text/uri-list", gtk::TargetFlags::SAME_APP, 0),
        ];
        browser.tree.drag_source_set(
            gdk::ModifierType::BUTTON1_MASK,
            &targets,
            gdk::DragAction::COPY,
        );
        {
            let weak = Rc::downgrade(&browser);
            browser.tree.connect_drag_data_get(move |_, _, data, _, _| {
                if let Some(b) = weak.upgrade() {
                    let uris = b.drag_uris();
                    let refs: Vec<_> = uris.iter().map(String::as_str).collect();
                    data.set_uris(&refs);
                }
            });
        }
        browser
            .sidebar
            .drag_dest_set(gtk::DestDefaults::ALL, &targets, gdk::DragAction::COPY);
        {
            let weak = Rc::downgrade(&browser);
            browser
                .sidebar
                .connect_drag_data_received(move |_, context, _, _, data, _, time| {
                    let mut success = false;
                    if let Some(b) = weak.upgrade() {
                        let paths: Vec<_> = data
                            .uris()
                            .iter()
                            .filter_map(|uri| gio::File::for_uri(uri).path())
                            .collect();
                        success = b.add_favorites(&paths) > 0;
                    }
                    context.drag_finish(success, false, time);
                });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.window.connect_key_press_event(move |_, event| {
                weak.upgrade()
                    .map_or(glib::Propagation::Proceed, |b| b.key(event))
            });
        }
        {
            let weak = Rc::downgrade(&browser);
            browser.window.connect_destroy(move |_| {
                if let Some(b) = weak.upgrade() {
                    b.alive.set(false);
                    if let Some(m) = b.monitor.borrow_mut().take() {
                        m.cancel();
                    }
                    if let Some(screen) = WidgetExt::screen(&b.window) {
                        gtk::StyleContext::remove_provider_for_screen(&screen, &b.css);
                    }
                }
            });
        }
        skin.set_popup(Some(&browser.appearance_menu()));
        browser.rebuild_sidebar();
        browser.apply_appearance();
        browser.window.show_all();
        let weak = Rc::downgrade(&browser);
        glib::timeout_add_local(Duration::from_millis(30), move || {
            let Some(b) = weak.upgrade() else {
                return glib::ControlFlow::Break;
            };
            if !b.alive.get() {
                return glib::ControlFlow::Break;
            }
            while let Ok(scan) = responses.try_recv() {
                b.finish(scan);
            }
            if b.changed
                .get()
                .is_some_and(|t| t.elapsed() > Duration::from_millis(250))
                && !b.nav.borrow().loading
            {
                b.changed.set(None);
                b.refresh();
            }
            glib::ControlFlow::Continue
        });
        browser.navigate(&start, true, None, true);
        browser
    }

    pub fn current(&self) -> PathBuf {
        self.nav.borrow().current.clone()
    }
    fn message(&self, text: &str) {
        self.status.set_text(text);
        self.status.set_tooltip_text(Some(text));
    }
    fn save(&self) {
        let result = self.prefs.borrow_mut().save();
        if let Err(e) = result {
            self.message(&format!("Could not save preferences: {e}"));
        }
    }
    fn go_text(self: &Rc<Self>, text: &str) {
        match core::location(text, &self.current()) {
            Ok(path) => self.navigate(&path, true, None, false),
            Err(e) => self.message(&e.to_string()),
        }
    }
    fn navigate(
        self: &Rc<Self>,
        path: &Path,
        record: bool,
        history_index: Option<usize>,
        fallback: bool,
    ) {
        let (target, select) = if path.is_file() {
            (
                path.parent().unwrap_or(Path::new("/")).to_path_buf(),
                Some(path.to_path_buf()),
            )
        } else {
            (path.to_path_buf(), None)
        };
        let mut nav = self.nav.borrow_mut();
        nav.generation += 1;
        nav.loading = true;
        let request = Request {
            generation: nav.generation,
            target: target.clone(),
            select,
            record,
            history_index,
            fallback,
        };
        drop(nav);
        self.message(&format!("Opening {} …", target.display()));
        if self.sender.send(request).is_err() {
            self.nav.borrow_mut().loading = false;
            self.message("The folder worker stopped. Please reopen Personal Files.");
        }
    }
    fn finish(self: &Rc<Self>, scan: Scan) {
        if scan.request.generation != self.nav.borrow().generation {
            return;
        }
        self.nav.borrow_mut().loading = false;
        let request = scan.request;
        match scan.result {
            Err(e) => {
                self.address.set_text(&self.current().to_string_lossy());
                self.message(&format!("Cannot open folder: {e}"));
                if request.fallback && request.target != core::home() {
                    self.navigate(&core::home(), true, None, false);
                }
            }
            Ok(items) => {
                {
                    let mut nav = self.nav.borrow_mut();
                    nav.current = request.target.clone();
                    nav.items = items;
                    if let Some(index) = request.history_index {
                        nav.index = index;
                    } else if request.record && nav.history.get(nav.index) != Some(&request.target)
                    {
                        let next = if nav.history.is_empty() {
                            0
                        } else {
                            nav.index + 1
                        };
                        nav.history.truncate(next);
                        nav.history.push(request.target.clone());
                        nav.index = nav.history.len() - 1;
                    }
                }
                self.address.set_text(&request.target.to_string_lossy());
                self.header.set_subtitle(Some(
                    &request
                        .target
                        .file_name()
                        .unwrap_or(request.target.as_os_str())
                        .to_string_lossy(),
                ));
                if request.record {
                    self.prefs.borrow_mut().visit(&request.target);
                }
                self.populate(request.select);
                self.rebuild_sidebar();
                self.apply_appearance();
                if request.record {
                    self.save();
                }
                {
                    let nav = self.nav.borrow();
                    self.back.set_sensitive(nav.index > 0);
                    self.forward
                        .set_sensitive(nav.index + 1 < nav.history.len());
                }
                self.watch();
                let warning = self.prefs.borrow_mut().warning.take();
                if let Some(warning) = warning {
                    self.message(&warning);
                }
            }
        }
    }
    fn populate(&self, select: Option<PathBuf>) {
        let selected = select.map(|p| vec![p]).unwrap_or_else(|| self.selected());
        let (key, descending) = {
            let p = self.prefs.borrow();
            (p.data.sort, p.data.descending)
        };
        let mut items = self.nav.borrow().items.clone();
        core::sort_entries(&mut items, key, descending);
        // Set lookup before model changes trigger selection signals.
        self.store.clear();
        *self.displayed.borrow_mut() = items.iter().map(|e| e.path.clone()).collect();
        for (index, entry) in items.iter().enumerate() {
            let icon = if entry.is_dir {
                "folder"
            } else if entry.symlink {
                "emblem-symbolic-link"
            } else {
                "text-x-generic"
            };
            let modified = glib::DateTime::from_unix_local(entry.modified as i64)
                .and_then(|d| d.format("%b %d, %Y  %H:%M"))
                .map(|s| s.to_string())
                .unwrap_or_else(|_| "—".into());
            let size = if entry.is_dir {
                "—".into()
            } else {
                core::size_label(entry.size)
            };
            let path = entry.path.to_string_lossy().into_owned();
            let name = entry.name();
            let iter = self.store.insert_with_values(
                None,
                &[
                    (0, &icon),
                    (1, &name),
                    (2, &modified),
                    (3, &size),
                    (4, &path),
                    (5, &(index as u32)),
                ],
            );
            if selected.contains(&entry.path) {
                self.tree.selection().select_iter(&iter);
            }
        }
        self.empty.set_visible(items.is_empty());
        self.update_status();
        for (sort, column) in &self.columns {
            column.set_sort_indicator(*sort == key);
            column.set_sort_order(if descending {
                gtk::SortType::Descending
            } else {
                gtk::SortType::Ascending
            });
        }
    }
    fn row_path(&self, row: &gtk::TreePath) -> Option<PathBuf> {
        let iter = self.store.iter(row)?;
        let index = self.store.value(&iter, 5).get::<u32>().ok()?;
        self.displayed.borrow().get(index as usize).cloned()
    }
    fn selected(&self) -> Vec<PathBuf> {
        self.tree
            .selection()
            .selected_rows()
            .0
            .iter()
            .filter_map(|row| self.row_path(row))
            .collect()
    }
    fn update_status(&self) {
        let n = self.selected().len();
        let nav = self.nav.borrow();
        self.message(&format!(
            "{} items{}  ·  {}",
            nav.items.len(),
            if n > 0 {
                format!(" · {n} selected")
            } else {
                String::new()
            },
            nav.current.display()
        ));
    }
    fn sort(&self, key: Sort) {
        {
            let mut p = self.prefs.borrow_mut();
            p.data.descending = if p.data.sort == key {
                !p.data.descending
            } else {
                key != Sort::Name
            };
            p.data.sort = key;
        }
        self.populate(None);
        self.save();
    }
    fn refresh(self: &Rc<Self>) {
        self.navigate(&self.current(), false, None, false);
    }
    fn go_history(self: &Rc<Self>, delta: isize) {
        let next = {
            let n = self.nav.borrow();
            let i = n.index as isize + delta;
            if i < 0 {
                None
            } else {
                n.history.get(i as usize).cloned().map(|p| (i as usize, p))
            }
        };
        if let Some((i, path)) = next {
            self.navigate(&path, true, Some(i), false);
        }
    }
    fn watch(self: &Rc<Self>) {
        if let Some(m) = self.monitor.borrow_mut().take() {
            m.cancel();
        }
        if let Ok(m) = gio::File::for_path(self.current())
            .monitor_directory(gio::FileMonitorFlags::NONE, None::<&gio::Cancellable>)
        {
            let weak = Rc::downgrade(self);
            m.connect_changed(move |_, _, _, _| {
                if let Some(b) = weak.upgrade() {
                    b.changed.set(Some(Instant::now()));
                }
            });
            *self.monitor.borrow_mut() = Some(m);
        }
    }
    fn open(self: &Rc<Self>, path: &Path) {
        if path.is_dir() {
            self.navigate(path, true, None, false);
        } else if let Err(e) = gio::AppInfo::launch_default_for_uri(
            &gio::File::for_path(path).uri(),
            None::<&gio::AppLaunchContext>,
        ) {
            self.message(&format!("Could not open file: {e}"));
        }
    }
    fn copy(&self, shell: bool, paths: Option<Vec<PathBuf>>) -> String {
        let mut paths = paths.unwrap_or_else(|| self.selected());
        if paths.is_empty() {
            paths.push(self.current());
        }
        let text = core::clipboard_text(&paths, shell);
        let clipboard = gtk::Clipboard::get(&gdk::SELECTION_CLIPBOARD);
        clipboard.set_text(&text);
        clipboard.store();
        self.message(&format!(
            "Copied {} {}path(s)",
            paths.len(),
            if shell { "shell-quoted " } else { "full " }
        ));
        text
    }
    fn toggle_favorite(self: &Rc<Self>) {
        let current = self.current();
        {
            let mut p = self.prefs.borrow_mut();
            if p.data.favorites.contains(&current) {
                p.unfavorite(&current);
            } else {
                p.favorite(&current);
            }
        }
        self.rebuild_sidebar();
        self.save();
    }
    fn add_favorites(self: &Rc<Self>, paths: &[PathBuf]) -> usize {
        let mut count = 0;
        {
            let mut p = self.prefs.borrow_mut();
            for path in paths {
                if path.is_dir() {
                    p.favorite(path);
                    count += 1;
                }
            }
        }
        self.rebuild_sidebar();
        self.save();
        self.message(&format!("Added {count} folder(s) to Favorites"));
        count
    }
    fn drag_uris(&self) -> Vec<String> {
        self.selected()
            .iter()
            .map(|p| gio::File::for_path(p).uri().to_string())
            .collect()
    }
    fn rebuild_sidebar(self: &Rc<Self>) {
        for child in self.sidebar.children() {
            self.sidebar.remove(&child);
        }
        let (favorites, recent, frequent) = {
            let p = self.prefs.borrow();
            (p.data.favorites.clone(), p.recent(7), p.frequent(5))
        };
        self.section(
            "PLACES",
            vec![
                core::home(),
                core::home().join("Desktop"),
                core::home().join("Downloads"),
                PathBuf::from("/"),
            ]
            .into_iter()
            .filter(|p| p.is_dir())
            .collect(),
        );
        self.section("FAVORITES", favorites.clone());
        if favorites.is_empty() {
            let hint = gtk::Label::new(Some("Drag folders here, or use ☆"));
            hint.set_xalign(0.);
            hint.set_margin_start(14);
            hint.style_context().add_class("hint");
            self.sidebar.pack_start(&hint, false, false, 5);
        }
        self.section("RECENT", recent);
        self.section("FREQUENT", frequent);
        self.pin.set_image(Some(&gtk::Image::from_icon_name(
            Some(if favorites.contains(&self.current()) {
                "starred-symbolic"
            } else {
                "non-starred-symbolic"
            }),
            gtk::IconSize::Button,
        )));
        self.sidebar.show_all();
    }
    fn section(self: &Rc<Self>, title: &str, paths: Vec<PathBuf>) {
        let heading = gtk::Label::new(Some(title));
        heading.set_xalign(0.);
        heading.style_context().add_class("section");
        self.sidebar.pack_start(&heading, false, false, 0);
        let list = gtk::ListBox::new();
        list.set_selection_mode(gtk::SelectionMode::None);
        for path in paths {
            let row = gtk::ListBoxRow::new();
            let line = gtk::Box::new(gtk::Orientation::Horizontal, 9);
            line.pack_start(
                &gtk::Image::from_icon_name(
                    Some(if path == core::home() {
                        "user-home-symbolic"
                    } else {
                        "folder-symbolic"
                    }),
                    gtk::IconSize::Menu,
                ),
                false,
                false,
                0,
            );
            let name = if path == core::home() {
                "Home".into()
            } else if path == Path::new("/") {
                "Computer".into()
            } else {
                path.file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned()
            };
            let label = gtk::Label::new(Some(&name));
            label.set_xalign(0.);
            label.set_ellipsize(pango::EllipsizeMode::Middle);
            label.set_max_width_chars(22);
            line.pack_start(&label, true, true, 0);
            row.add(&line);
            row.set_tooltip_text(Some(&path.to_string_lossy()));
            {
                let weak = Rc::downgrade(self);
                let path = path.clone();
                row.connect_activate(move |_| {
                    if let Some(b) = weak.upgrade() {
                        b.navigate(&path, true, None, false);
                    }
                });
            }
            {
                let weak = Rc::downgrade(self);
                let path = path.clone();
                row.connect_button_press_event(move |_, event| {
                    if event.button() == 3 {
                        if let Some(b) = weak.upgrade() {
                            b.path_menu(vec![path.clone()])
                                .popup_at_pointer(Some(event));
                        }
                        glib::Propagation::Stop
                    } else {
                        glib::Propagation::Proceed
                    }
                });
            }
            list.add(&row);
        }
        self.sidebar.pack_start(&list, false, false, 0);
    }
    fn menu_item(menu: &gtk::Menu, title: &str, callback: impl Fn() + 'static) {
        let item = gtk::MenuItem::with_label(title);
        item.connect_activate(move |_| callback());
        menu.append(&item);
    }
    fn path_menu(self: &Rc<Self>, paths: Vec<PathBuf>) -> gtk::Menu {
        let menu = gtk::Menu::new();
        menu.set_attach_widget(Some(&self.window));
        {
            let weak = Rc::downgrade(self);
            let paths = paths.clone();
            Self::menu_item(&menu, "Open", move || {
                if let Some(b) = weak.upgrade() {
                    b.open(&paths[0]);
                }
            });
        }
        for (title, shell) in [("Copy Full Path", false), ("Copy Shell-Quoted Path", true)] {
            let weak = Rc::downgrade(self);
            let paths = paths.clone();
            Self::menu_item(&menu, title, move || {
                if let Some(b) = weak.upgrade() {
                    b.copy(shell, Some(paths.clone()));
                }
            });
        }
        if paths.iter().any(|p| p.is_dir()) {
            let weak = Rc::downgrade(self);
            let paths = paths.clone();
            Self::menu_item(&menu, "Add to Favorites", move || {
                if let Some(b) = weak.upgrade() {
                    b.add_favorites(&paths);
                }
            });
        }
        if paths
            .iter()
            .any(|p| self.prefs.borrow().data.favorites.contains(p))
        {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, "Remove from Favorites", move || {
                if let Some(b) = weak.upgrade() {
                    {
                        let mut p = b.prefs.borrow_mut();
                        for path in &paths {
                            p.unfavorite(path);
                        }
                    }
                    b.rebuild_sidebar();
                    b.save();
                }
            });
        }
        menu.connect_selection_done(|m| m.detach());
        menu.show_all();
        menu
    }
    fn appearance_menu(self: &Rc<Self>) -> gtk::Menu {
        let menu = gtk::Menu::new();
        for (key, title) in [
            ("silver", "Silver"),
            ("midnight", "Midnight"),
            ("aurora", "Aurora"),
            ("auto", "Automatic · match folder contents"),
        ] {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, title, move || {
                if let Some(b) = weak.upgrade() {
                    b.set_theme(key);
                }
            });
        }
        menu.append(&gtk::SeparatorMenuItem::new());
        {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, "Choose Background Image…", move || {
                if let Some(b) = weak.upgrade() {
                    b.choose_image();
                }
            });
        }
        {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, "Remove Background Image", move || {
                if let Some(b) = weak.upgrade() {
                    b.set_image(Path::new(""));
                }
            });
        }
        menu.append(&gtk::SeparatorMenuItem::new());
        {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, "Keyboard Shortcuts", move || {
                if let Some(b) = weak.upgrade() {
                    b.shortcuts();
                }
            });
        }
        {
            let weak = Rc::downgrade(self);
            Self::menu_item(&menu, "Clear Visit History", move || {
                if let Some(b) = weak.upgrade() {
                    b.prefs.borrow_mut().data.visits.clear();
                    b.rebuild_sidebar();
                    b.save();
                    b.message("Visit history cleared. Favorites kept.");
                }
            });
        }
        menu.show_all();
        menu
    }
    fn set_theme(&self, theme: &str) {
        self.prefs.borrow_mut().data.theme = theme.into();
        self.apply_appearance();
        self.save();
    }
    fn set_image(&self, path: &Path) {
        if !path.as_os_str().is_empty() {
            if let Err(e) = gdk_pixbuf::Pixbuf::from_file_at_scale(path, 64, 64, true) {
                self.message(&format!("Cannot use this image: {e}"));
                return;
            }
        }
        self.prefs.borrow_mut().data.image = path.into();
        self.apply_appearance();
        self.save();
    }
    fn choose_image(&self) {
        let dialog = gtk::FileChooserDialog::with_buttons(
            Some("Choose a background image"),
            Some(&self.window),
            gtk::FileChooserAction::Open,
            &[
                ("Cancel", gtk::ResponseType::Cancel),
                ("Use Image", gtk::ResponseType::Ok),
            ],
        );
        let filter = gtk::FileFilter::new();
        filter.set_name(Some("Images"));
        filter.add_pixbuf_formats();
        dialog.add_filter(filter);
        if dialog.run() == gtk::ResponseType::Ok {
            if let Some(path) = dialog.filename() {
                self.set_image(&path);
            }
        }
        dialog.close();
    }
    fn apply_appearance(&self) {
        let (theme, image) = {
            let p = self.prefs.borrow();
            (
                appearance::effective_theme(&p.data.theme, &self.nav.borrow().items),
                if p.data.image.is_file() {
                    p.data.image.clone()
                } else {
                    PathBuf::new()
                },
            )
        };
        if let Err(e) = self
            .css
            .load_from_data(appearance::stylesheet(&theme, &image).as_bytes())
        {
            self.message(&format!("Appearance could not load: {e}"));
        }
    }
    fn shortcuts(&self) {
        let dialog = gtk::MessageDialog::new(
            Some(&self.window),
            gtk::DialogFlags::MODAL,
            gtk::MessageType::Info,
            gtk::ButtonsType::Close,
            "Personal Files · Keyboard Shortcuts",
        );
        dialog.set_secondary_text(Some("Ctrl+L     Focus path bar\nCtrl+C     Copy full path(s)\nCtrl+Shift+C     Copy shell-quoted path(s)\nCtrl+D     Toggle favorite folder\nCtrl+R / F5     Refresh\nAlt+Left / Right     Back / forward\nAlt+Up     Parent folder\nEnter     Open selected item\n\nDrop folders into the sidebar to favorite them.\nClick Name, Modified, or Size again to reverse sorting.\nHidden files are always visible."));
        dialog.run();
        dialog.close();
    }
    fn key(self: &Rc<Self>, event: &gdk::EventKey) -> glib::Propagation {
        let ctrl = event.state().contains(gdk::ModifierType::CONTROL_MASK);
        let shift = event.state().contains(gdk::ModifierType::SHIFT_MASK);
        let alt = event.state().contains(gdk::ModifierType::MOD1_MASK);
        let key = event.keyval().to_lower();
        if ctrl && key == gdk::keys::constants::l {
            self.address.grab_focus();
            self.address.select_region(0, -1);
            return glib::Propagation::Stop;
        }
        if ctrl && key == gdk::keys::constants::c {
            if self.address.has_focus() {
                return glib::Propagation::Proceed;
            }
            self.copy(shift, None);
        } else if ctrl && key == gdk::keys::constants::d {
            self.toggle_favorite();
        } else if (ctrl && key == gdk::keys::constants::r) || key == gdk::keys::constants::F5 {
            self.refresh();
        } else if alt && key == gdk::keys::constants::Left {
            self.go_history(-1);
        } else if alt && key == gdk::keys::constants::Right {
            self.go_history(1);
        } else if alt && key == gdk::keys::constants::Up {
            let parent = self
                .current()
                .parent()
                .unwrap_or(Path::new("/"))
                .to_path_buf();
            self.navigate(&parent, true, None, false);
        } else if !self.address.has_focus()
            && (key == gdk::keys::constants::Return || key == gdk::keys::constants::KP_Enter)
        {
            if let Some(path) = self.selected().first() {
                self.open(path);
            }
        } else {
            return glib::Propagation::Proceed;
        }
        glib::Propagation::Stop
    }
}

pub fn run() -> i32 {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.first().is_some_and(|s| s == "--help" || s == "-h") {
        println!("Personal Files — Ubuntu file browser\nUsage: personal-files [PATH]");
        return 0;
    }
    if args.len() > 1 {
        eprintln!("Usage: personal-files [PATH]");
        return 2;
    }
    if let Err(e) = gtk::init() {
        eprintln!("Personal Files needs an Ubuntu graphical desktop: {e}");
        return 1;
    }
    let start = args.first().map(PathBuf::from).map(|p| {
        if p.is_absolute() {
            p
        } else {
            std::env::current_dir()
                .unwrap_or_else(|_| core::home())
                .join(p)
        }
    });
    let app = gtk::Application::new(
        Some("io.monoclaw.PersonalFiles"),
        gio::ApplicationFlags::NON_UNIQUE,
    );
    let windows: Rc<RefCell<Vec<Rc<Browser>>>> = Rc::new(RefCell::new(vec![]));
    let keep = windows.clone();
    app.connect_activate(move |app| {
        let browser = Browser::new(
            app,
            start.clone(),
            Preferences::load(Preferences::default_path()),
        );
        keep.borrow_mut().push(browser);
    });
    app.run_with_args::<&str>(&[]).value()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn drain() {
        let context = glib::MainContext::default();
        while context.pending() {
            context.iteration(false);
        }
    }
    fn wait(browser: &Browser) {
        let deadline = Instant::now() + Duration::from_secs(5);
        while browser.nav.borrow().loading && Instant::now() < deadline {
            drain();
            thread::sleep(Duration::from_millis(10));
        }
        drain();
        assert!(!browser.nav.borrow().loading, "folder scan timed out");
    }
    fn select(browser: &Browser, name: &str) -> gtk::TreePath {
        browser.tree.selection().unselect_all();
        let index = browser
            .displayed
            .borrow()
            .iter()
            .position(|p| p.file_name().unwrap_or_default() == name)
            .unwrap();
        let row = gtk::TreePath::from_indicesv(&[index as i32]);
        browser.tree.selection().select_path(&row);
        row
    }

    #[test]
    #[ignore = "Needs a real graphical display or xvfb-run; uses only temporary fixture files"]
    fn desktop_story() {
        gtk::init().expect("GTK must connect to a graphical display");
        let app = gtk::Application::new(
            Some("io.monoclaw.PersonalFiles.Tests"),
            gio::ApplicationFlags::NON_UNIQUE,
        );
        app.register(None::<&gio::Cancellable>).unwrap();
        let temp = TempDir::new().unwrap();
        let root = temp.path();
        let physics = root.join("Library/long path/Physics");
        fs::create_dir_all(physics.join("Topics")).unwrap();
        fs::write(physics.join(".hidden"), "fixture").unwrap();
        let filename = "a b's $notes.txt";
        fs::write(physics.join(filename), "fixture").unwrap();
        let prefs_path = root.join("config/preferences.json");
        let browser = Browser::new(
            &app,
            Some(physics.clone()),
            Preferences::load(prefs_path.clone()),
        );
        wait(&browser);
        assert_eq!(browser.current(), physics);
        assert!(browser
            .displayed
            .borrow()
            .contains(&physics.join(".hidden")));
        eprintln!("PASS startup and hidden files");
        browser.address.set_text("Topics");
        browser.address.emit_activate();
        wait(&browser);
        assert_eq!(browser.current(), physics.join("Topics"));
        browser.address.set_text(&physics.to_string_lossy());
        browser.address.emit_activate();
        wait(&browser);
        eprintln!("PASS absolute and relative path entry");
        browser.pin.emit_clicked();
        assert!(browser.prefs.borrow().data.favorites.contains(&physics));
        browser.navigate(root, true, None, false);
        wait(&browser);
        let favorites = browser
            .sidebar
            .children()
            .into_iter()
            .filter_map(|w| w.downcast::<gtk::ListBox>().ok())
            .nth(1)
            .unwrap();
        favorites.row_at_index(0).unwrap().emit_activate();
        wait(&browser);
        assert_eq!(browser.current(), physics);
        eprintln!("PASS favorite button and sidebar activation");
        select(&browser, filename);
        browser.copy(false, None);
        let clipboard = gtk::Clipboard::get(&gdk::SELECTION_CLIPBOARD);
        assert_eq!(
            clipboard.wait_for_text().unwrap().as_str(),
            physics.join(filename).to_str().unwrap()
        );
        let text = browser.copy(true, None);
        assert_eq!(clipboard.wait_for_text().unwrap().as_str(), text);
        assert_eq!(
            text,
            core::shell_quote(physics.join(filename).to_str().unwrap())
        );
        eprintln!("PASS real clipboard plain and shell-quoted paths");
        let menu = browser.path_menu(vec![physics.clone()]);
        menu.children()[1]
            .clone()
            .downcast::<gtk::MenuItem>()
            .unwrap()
            .emit_activate();
        assert_eq!(
            clipboard.wait_for_text().unwrap().as_str(),
            physics.to_str().unwrap()
        );
        menu.detach();
        eprintln!("PASS context menu path copy");
        browser.columns[2].1.clicked();
        assert_eq!(browser.prefs.borrow().data.sort, Sort::Size);
        assert!(browser.prefs.borrow().data.descending);
        assert!(browser.displayed.borrow()[0].is_dir());
        browser.columns[2].1.clicked();
        assert!(!browser.prefs.borrow().data.descending);
        browser.columns[1].1.clicked();
        assert_eq!(browser.prefs.borrow().data.sort, Sort::Modified);
        eprintln!("PASS sort column signals and reversal");
        let row = select(&browser, "Topics");
        browser.tree.row_activated(&row, &browser.columns[0].1);
        wait(&browser);
        assert_eq!(browser.current(), physics.join("Topics"));
        browser.go_text(physics.join(".hidden").to_str().unwrap());
        wait(&browser);
        assert_eq!(browser.current(), physics);
        assert_eq!(browser.selected(), vec![physics.join(".hidden")]);
        eprintln!("PASS row activation and file-path selection");
        browser.navigate(&root.join("missing"), true, None, false);
        wait(&browser);
        assert_eq!(browser.current(), physics);
        assert!(browser.status.text().starts_with("Cannot open"));
        assert!(!browser
            .prefs
            .borrow()
            .data
            .visits
            .contains_key(&root.join("missing")));
        eprintln!("PASS failed navigation preserves current folder and history");
        browser.navigate(root, true, None, false);
        wait(&browser);
        browser.go_history(-1);
        wait(&browser);
        assert_eq!(browser.current(), physics);
        browser.go_history(1);
        wait(&browser);
        assert_eq!(browser.current(), root);
        let count = browser.prefs.borrow().data.visits[root].count;
        browser.refresh();
        wait(&browser);
        assert_eq!(browser.prefs.borrow().data.visits[root].count, count);
        eprintln!("PASS back, forward, refresh without inflated visits");
        browser.navigate(&physics, true, None, false);
        wait(&browser);
        select(&browser, "Topics");
        let uris = browser.drag_uris();
        assert_eq!(
            uris,
            vec![gio::File::for_path(physics.join("Topics"))
                .uri()
                .to_string()]
        );
        let dropped: Vec<_> = uris
            .iter()
            .filter_map(|u| gio::File::for_uri(u).path())
            .collect();
        assert_eq!(browser.add_favorites(&dropped), 1);
        assert!(browser
            .prefs
            .borrow()
            .data
            .favorites
            .contains(&physics.join("Topics")));
        eprintln!("PASS drag URI payload and favorite drop handling");
        for theme in ["silver", "midnight", "aurora", "auto"] {
            browser.set_theme(theme);
            assert!(!browser.status.text().contains("Appearance could not load"));
        }
        let image = root.join("background's image.png");
        let pixbuf =
            gdk_pixbuf::Pixbuf::new(gdk_pixbuf::Colorspace::Rgb, false, 8, 32, 32).unwrap();
        pixbuf.fill(0x37679fff);
        pixbuf.savev(&image, "png", &[]).unwrap();
        browser.set_image(&image);
        assert_eq!(browser.prefs.borrow().data.image, image);
        assert!(!browser.status.text().contains("Appearance could not load"));
        browser.set_image(&root.join("missing.png"));
        assert_eq!(browser.prefs.borrow().data.image, image);
        browser.set_image(Path::new(""));
        assert!(browser.prefs.borrow().data.image.as_os_str().is_empty());
        eprintln!("PASS all GTK skins, image validation and removal");
        let count = browser.prefs.borrow().data.visits[&physics].count;
        fs::write(physics.join("new.txt"), "fixture").unwrap();
        let deadline = Instant::now() + Duration::from_secs(4);
        while !browser
            .displayed
            .borrow()
            .contains(&physics.join("new.txt"))
            && Instant::now() < deadline
        {
            drain();
            thread::sleep(Duration::from_millis(20));
        }
        assert!(browser
            .displayed
            .borrow()
            .contains(&physics.join("new.txt")));
        assert_eq!(browser.prefs.borrow().data.visits[&physics].count, count);
        eprintln!("PASS real filesystem monitoring without inflated visits");
        let generation = browser.nav.borrow().generation;
        browser.finish(Scan {
            request: Request {
                generation: generation - 1,
                target: root.into(),
                select: None,
                record: true,
                history_index: None,
                fallback: false,
            },
            result: Ok(vec![]),
        });
        assert_eq!(browser.current(), physics);
        eprintln!("PASS stale background result rejected");
        browser.window.close();
        drain();
        drop(browser);
        let browser = Browser::new(&app, None, Preferences::load(prefs_path));
        wait(&browser);
        assert_eq!(browser.current(), physics);
        assert!(browser.prefs.borrow().data.favorites.contains(&physics));
        assert!(browser.prefs.borrow().recent(10).contains(&physics));
        eprintln!("PASS fresh-window restart persistence");
        browser.set_theme("silver");
        if let Some(path) = std::env::var_os("PERSONAL_FILES_SCREENSHOT") {
            drain();
            thread::sleep(Duration::from_millis(100));
            drain();
            if let Some(window) = browser.window.window() {
                let (w, h) = (window.width(), window.height());
                let pixbuf = window.pixbuf(0, 0, w, h).unwrap();
                pixbuf.savev(PathBuf::from(path), "png", &[]).unwrap();
            }
        }
        browser.prefs.borrow_mut().data.visits.clear();
        browser.rebuild_sidebar();
        browser.save();
        assert_eq!(browser.prefs.borrow().data.favorites.len(), 2);
        assert!(browser.prefs.borrow().data.visits.is_empty());
        eprintln!("PASS clearing visits retains favorites");
        browser.window.close();
        drain();
    }
}
