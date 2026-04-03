# 1. Get total commits where Claude is the actual Git Author
total=$(git log -i --author="Claude" --format="%H" | grep -v '^$' | wc -l | tr -d ' ')

if [ "$total" -eq 0 ]; then
  echo "Claude is not listed as the Git Author anymore. If you still see it, GitHub is caching the old page. Clear your browser cache or wait a few minutes."
else
  remove_count=$(( total * 80 / 100 ))
  
  # 2. Save the oldest 80% to a new target list
  git log -i --author="Claude" --format="%H" | tail -n "$remove_count" > /tmp/claude_author_strip.txt
  
  echo "Found $total commits authored by Claude. Reclaiming $remove_count of them..."
  
  # 3. Run the environment filter to rewrite the Author and Committer metadata
  git filter-branch --force --env-filter '
  if grep -qx "$GIT_COMMIT" /tmp/claude_author_strip.txt 2>/dev/null; then
      export GIT_AUTHOR_NAME="henrique-simoes"
      export GIT_AUTHOR_EMAIL="simoeshz@gmail.com"
      export GIT_COMMITTER_NAME="henrique-simoes"
      export GIT_COMMITTER_EMAIL="simoeshz@gmail.com"
  fi
  ' -- --all
fi