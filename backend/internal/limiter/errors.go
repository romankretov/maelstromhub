package limiter

import "errors"

var ErrDeferred = errors.New("non-critical request deferred due to low rate-limit budget")
