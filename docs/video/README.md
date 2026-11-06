# Walkthrough video: how to rebuild it

Draft built 2026-11-06 (about 2 minutes, 1080p, burned-in captions plus an .srt). Rebuild it whenever the wizard copy changes. The narration script lives in `SCENES` in build.py, and the captions match it.

```
W=<scratch dir>; python3 -m venv $W/tts && $W/tts/bin/pip install piper-tts segno pillow
# voice (free, local): rhasspy/piper-voices en_US-lessac-medium .onnx + .onnx.json -> $W/voices/
.venv/bin/python docs/video/shots.py $W/shots          # real wizard, fake person "Pat Example"
cp docs/video/build.py $W/ && $W/tts/bin/python $W/build.py $W $W/free-my-id-walkthrough.mp4
```

shots.py runs the real wizard server against a temp FREEMYID_HOME with the test key, blocks every non-local request, never installs the scheduler task, and uses only fake data. The .mp4 isn't committed (it's a binary): publish it to YouTube or attach it to a release.
