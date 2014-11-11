import time
import contextlib

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import scoped_session

sessionmaker_ = sessionmaker


@contextlib.contextmanager
def no_context(q):
    yield q


@contextlib.contextmanager
def close_session_connection(q):
    try:
        yield q
    finally:
        q.session.connection().close()


def pooled_sessionmaker(pool, sessionmaker=sessionmaker_):
    def factory(*args,**kwargs):
        connection = pool.connect()
        session = sessionmaker(bind=connection)
        return session
    return factory


def use_new_scoped_session(sessionmaker=sessionmaker_):
    def transform(original):
        Session = scoped_session(sessionmaker())
        query = original.with_session(Session())
        return query
    return transform


def close_on_finish(future, query):
    query.session.connection().close()


def transform_and_execute(query, transform, context=no_context):
    transformed = query.with_transformation(transform)
    with context(transformed):
        for result in transformed:
            yield result


def chain_transformations(*transformers):
    def transform(original):
        query = original
        for transformer in transformers:
            query = query.with_transformation(transformer)
        return query
    return transform


def transform_in_new_session(transform_session, inner_transform):
    def transform(original):
        query = original
        query = query.with_transformation(transform_session)
        query = query.with_transformation(inner_transform)
        return query
    return transform


def map_sessions_over_transformations(transformers, sessionmaker, query, **kwargs):
    apply_scoped_session = use_new_scoped_session(sessionmaker)
    for inner_transformer in transformers:
        outer_transformer = transform_in_new_session(apply_scoped_session, inner_transform)
        yield query.promise_with_transformation(outer_transformer, **kwargs)


