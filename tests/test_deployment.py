from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compose = (
            ROOT / "compose.preview.yml"
        ).read_text(encoding="utf-8")

        self.nginx = (
            ROOT / "deploy" / "nginx.conf"
        ).read_text(encoding="utf-8")

        self.update_script = (
            ROOT / "scripts" / "update-map.sh"
        ).read_text(encoding="utf-8")

        self.prune_script = (
            ROOT / "scripts" / "prune-database.sh"
        ).read_text(encoding="utf-8")

        self.check_script_path = (
            ROOT / "scripts" / "check-project.sh"
        )
        self.check_script = self.check_script_path.read_text(
            encoding="utf-8"
        )

        self.prune_service = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-prune.service"
        ).read_text(encoding="utf-8")

        self.prune_timer = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-prune.timer"
        ).read_text(encoding="utf-8")

        self.backup_script_path = (
            ROOT / "scripts" / "backup-database.sh"
        )
        self.backup_script = (
            self.backup_script_path.read_text(
                encoding="utf-8"
            )
        )
        self.backup_service = (
            ROOT / "deploy" / "systemd"
            / "mesh-noroeste-backup.service"
        ).read_text(encoding="utf-8")
        self.backup_timer = (
            ROOT / "deploy" / "systemd"
            / "mesh-noroeste-backup.timer"
        ).read_text(encoding="utf-8")

        self.update_service = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-update@.service"
        ).read_text(encoding="utf-8")

        self.ozulo_timer = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-ozulo.timer"
        ).read_text(encoding="utf-8")

        self.meshcore_hub_timer = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-meshcore-hub.timer"
        ).read_text(encoding="utf-8")

        self.analysis_script_path = (
            ROOT
            / "scripts"
            / "update-configuration-analysis.py"
        )
        self.analysis_script = (
            self.analysis_script_path.read_text(
                encoding="utf-8"
            )
        )

        self.analysis_module_path = (
            ROOT
            / "backend"
            / "mesh_noroeste"
            / "configuration_analysis.py"
        )
        self.analysis_module = (
            self.analysis_module_path.read_text(
                encoding="utf-8"
            )
        )

        self.analysis_service = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-analysis.service"
        ).read_text(encoding="utf-8")

        self.analysis_timer = (
            ROOT
            / "deploy"
            / "systemd"
            / "mesh-noroeste-analysis.timer"
        ).read_text(encoding="utf-8")

    def test_preview_is_bound_only_to_loopback(self) -> None:
        self.assertIn(
            '"127.0.0.1:8096:80"',
            self.compose,
        )

    def test_mounts_are_read_only(self) -> None:
        self.assertIn(
            "./frontend:/usr/share/nginx/html:ro",
            self.compose,
        )
        self.assertIn(
            "./deploy/nginx.conf:"
            "/etc/nginx/conf.d/default.conf:ro",
            self.compose,
        )

    def test_preview_joins_caddy_network(self) -> None:
        self.assertIn("s3net:", self.compose)
        self.assertIn("external: true", self.compose)
        self.assertIn(
            "- mesh-noroeste-web",
            self.compose,
        )

    def test_missing_assets_return_404(self) -> None:
        self.assertIn(
            "try_files $uri $uri/ =404;",
            self.nginx,
        )
        self.assertNotIn(
            "try_files $uri /index.html",
            self.nginx,
        )

    def test_public_data_are_not_cached(self) -> None:
        self.assertIn("~^/data/", self.nginx)
        self.assertIn('"no-store"', self.nginx)

    def test_project_validation_is_reproducible(
        self,
    ) -> None:
        self.assertTrue(
            self.check_script_path.stat().st_mode & 0o111
        )

        for expected in (
            "-m compileall -q",
            "sh -n",
            "node --check",
            "node:22-alpine",
            "-m unittest discover",
            "tests/validate_contracts.py",
            "git --no-pager diff --check",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.check_script)

    def test_automatic_updates_use_compact_logs(
        self,
    ) -> None:
        self.assertEqual(
            self.update_script.count("--compact"),
            3,
        )

    def test_ozulo_updates_are_declared(
        self,
    ) -> None:
        self.assertIn(
            "meshview|malha|ozulo|meshcore",
            self.update_script,
        )
        self.assertIn(
            "OnUnitActiveSec=30min",
            self.ozulo_timer,
        )
        self.assertIn(
            "Unit=mesh-noroeste-update@ozulo.service",
            self.ozulo_timer,
        )

    def test_meshcore_hub_updates_are_declared(
        self,
    ) -> None:
        self.assertIn(
            "meshview|malha|ozulo|meshcore|meshcore-hub",
            self.update_script,
        )
        self.assertIn(
            '"collect-$mode"',
            self.update_script,
        )
        self.assertIn(
            "OnUnitActiveSec=5min",
            self.meshcore_hub_timer,
        )
        self.assertIn(
            "Persistent=true",
            self.meshcore_hub_timer,
        )
        self.assertIn(
            (
                "Unit=mesh-noroeste-update@"
                "meshcore-hub.service"
            ),
            self.meshcore_hub_timer,
        )

    def test_configuration_warnings_are_deployed(
        self,
    ) -> None:
        self.assertIn(
            '--output "$public_dir"',
            self.update_script,
        )
        self.assertNotIn(
            'data_dir=',
            self.update_script,
        )
        self.assertNotIn(
            'for name in nodes edges',
            self.update_script,
        )
        self.assertNotIn(
            "ReadWritePaths=/srv/mesh-noroeste/data",
            self.update_service,
        )
        self.assertIn(
            "MESH_CONFIGURATION_WARNINGS_PATH="
            "/srv/mesh-noroeste/cache/"
            "configuration-analysis.json",
            self.update_service,
        )
        self.assertNotIn(
            "meshtastic-map_json-raw",
            self.update_service,
        )
        self.assertTrue(
            self.analysis_script_path.stat().st_mode
            & 0o111
        )

        for expected in (
            "from mesh_noroeste.configuration_analysis "
            "import main",
            "raise SystemExit(main())",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    self.analysis_script,
                )

        for expected in (
            "https://meshview.meshtastic.es",
            "def run_analysis(",
            "def atomic_write(",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    self.analysis_module,
                )

        self.assertIn(
            "EnvironmentFile=/etc/mesh-noroeste/"
            "mesh-noroeste.env",
            self.analysis_service,
        )

        self.assertNotIn(
            "CCAA_CACHE_PATH",
            self.analysis_service,
        )

        self.assertIn(
            "ExecStart=/srv/mesh-noroeste/"
            "scripts/update-configuration-analysis.py",
            self.analysis_service,
        )
        self.assertIn(
            "ReadWritePaths=/srv/mesh-noroeste/cache",
            self.analysis_service,
        )
        self.assertIn(
            "OnUnitActiveSec=6h",
            self.analysis_timer,
        )
        self.assertIn(
            "Persistent=true",
            self.analysis_timer,
        )

    def test_database_backup_is_scheduled_daily(
        self,
    ) -> None:
        self.assertTrue(
            self.backup_script_path.stat().st_mode & 0o111
        )
        for expected in (
            'flock -w 300',
            'VACUUM INTO',
            'PRAGMA quick_check;',
            'sha256sum',
            '-mmin +43200',
        ):
            self.assertIn(expected, self.backup_script)

        self.assertIn(
            'scripts/backup-database.sh',
            self.backup_service,
        )
        self.assertIn(
            'ReadWritePaths=/srv/mesh-noroeste/state',
            self.backup_service,
        )
        self.assertIn(
            'OnCalendar=*-*-* 23:15:00',
            self.backup_timer,
        )
        self.assertIn('Persistent=true', self.backup_timer)

    def test_database_pruning_is_scheduled_daily(
        self,
    ) -> None:
        self.assertIn(
            "-m mesh_noroeste.cli",
            self.prune_script,
        )
        self.assertIn(
            "prune",
            self.prune_script,
        )
        self.assertEqual(
            self.prune_script.count("--compact"),
            2,
        )
        self.assertIn(
            "flock -w 300",
            self.prune_script,
        )
        self.assertIn(
            "ExecStart=/srv/mesh-noroeste/"
            "scripts/prune-database.sh",
            self.prune_service,
        )
        self.assertIn(
            "OnCalendar=daily",
            self.prune_timer,
        )
        self.assertIn(
            "Persistent=true",
            self.prune_timer,
        )

    def test_geolocation_is_allowed_only_for_self(
        self,
    ) -> None:
        self.assertIn(
            'Permissions-Policy '
            '"geolocation=(self), microphone=(), camera=()"',
            self.nginx,
        )


if __name__ == "__main__":
    unittest.main()
