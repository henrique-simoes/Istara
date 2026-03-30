cask "istara" do
  version "2026.03.30.6"
  sha256 "0b65d48458e8d8b4146b220e6b90ee1c62759711511d25ce9db2372a06fa26a3"

  url "https://github.com/henrique-simoes/Istara/releases/download/v#{version}/Istara-#{version}.dmg",
      verified: "github.com/henrique-simoes/Istara/"

  name "Istara"
  desc "Local-first AI agents for UX Research — your data never leaves your machine"
  homepage "https://github.com/henrique-simoes/Istara"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates true
  depends_on macos: ">= :ventura"

  app "Istara.app"

  zap trash: [
    "~/Library/Application Support/com.istara.desktop",
    "~/Library/Caches/com.istara.desktop",
    "~/Library/LaunchAgents/com.istara.server.plist",
    "~/Library/Logs/Istara",
    "~/Library/Preferences/com.istara.desktop.plist",
    "~/Library/Saved Application State/com.istara.desktop.savedState",
    "~/.istara",
  ]
end
