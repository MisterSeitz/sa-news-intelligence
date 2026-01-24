# First, specify the base Docker image.
# You can see the Docker images from Apify at https://hub.docker.com/r/apify/.
# You can also use any other image from Docker Hub.
FROM apify/actor-python:3.13

# Second, copy just requirements.txt into the Actor image,
# since it should be the only file that affects the dependency install in the next step,
# in order to speed up the build
COPY --chown=myuser:myuser requirements.txt ./

# Install the packages specified in requirements.txt,
# Print the installed Python version, pip version
# and all installed packages with their versions for debugging
# ADDED --no-cache-dir and switched to explicit pip3/python3 commands to force a clean install.
RUN echo "Python version:" \
 && python3 --version \
 && echo "Pip version:" \
 && pip3 --version \
 && echo "Installing dependencies:" \
 && pip3 install --no-cache-dir -r requirements.txt \
 && echo "All installed Python packages:" \
 && pip3 freeze

# Next, copy the remaining files and directories with the source code.
# Since we do this after installing the dependencies, quick build will be really fast
# for most source file changes.
COPY --chown=myuser:myuser . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python3 -m compileall -q src/

# Specify how to launch the source code of your Actor.
# CHANGED to run src/main.py directly to resolve module path issues.
CMD ["python3", "-m", "src.main"]