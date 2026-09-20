# Development endpoint image; build the tested native and Rust images first.
FROM jocky-agent:foundation AS agent
FROM jocky-control-plane:latest
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=agent /src/target/debug/jocky-agent /usr/local/bin/jocky-agent
RUN mkdir /endpoint && chown 10001:10001 /endpoint
USER 10001
WORKDIR /endpoint
ENTRYPOINT ["jocky-agent"]
CMD ["doctor"]
