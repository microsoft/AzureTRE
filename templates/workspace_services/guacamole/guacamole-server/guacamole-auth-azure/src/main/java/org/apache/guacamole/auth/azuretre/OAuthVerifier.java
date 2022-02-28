/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.guacamole.auth.azuretre;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

public class OAuthVerifier {
    /**
     * The in-memory store of {@link CodeChallengeState}.
     */
    private static final Map<String, CodeChallengeState> challenges = new HashMap<>();

    /**
     * The minimum amount of time to wait between sweeping expired state from the
     * Map.
     */
    private static final long SWEEP_INTERVAL = 60000L;

    /**
     * The minimum age for state to remain valid. Default to 10 min.
     */
    private static final long STATE_MAX_AGE = 10L * 60000L;

    /**
     * The timestamp of the last expired state sweep.
     */
    private long lastSweep = System.currentTimeMillis();

    /**
     * Initializes a new instance of the {@link OAuthVerifier} class.
     */
    public OAuthVerifier() {
    }

    public CodeChallengeState createCodeChallenge() {
        // Sweep expired state if enough time has passed
        sweepExpiredState();

        CodeChallengeState state = new CodeChallengeState(STATE_MAX_AGE);
        challenges.put(state.getId(), state);
        return state;
    }

    /**
     * Given the state identifier returned with the auth code response, retrieves
     * the stored state needed for validation. Once called the state is removed from
     * the store, so this can only be used once.
     *
     * @param id The state identifier.
     * @return If the state id is valid and the state has not expired a
     *         {@link CodeChallengeState}, otherwise null.
     */
    public CodeChallengeState getState(String id) {
        // Sweep expired state if enough time has passed
        sweepExpiredState();

        CodeChallengeState state = challenges.remove(id);
        if (state != null && state.isStillValid())
            return state;

        return null;
    }

    /**
     * Iterates through the Map of state, removing any that has exceeded its
     * expiration timestamp. If insufficient time has elapsed since the last sweep,
     * as dictated by SWEEP_INTERVAL, this function has no effect.
     */
    private void sweepExpiredState() {

        // Do not sweep until enough time has elapsed since the last sweep
        long currentTime = System.currentTimeMillis();
        if (currentTime - lastSweep < SWEEP_INTERVAL)
            return;

        // Record time of sweep
        lastSweep = currentTime;

        // For each stored state
        Iterator<Map.Entry<String, CodeChallengeState>> entries = challenges.entrySet().iterator();
        while (entries.hasNext()) {
            // Remove all entries which have expired
            Map.Entry<String, CodeChallengeState> current = entries.next();
            if (!current.getValue().isStillValid())
                entries.remove();
        }
    }
}


