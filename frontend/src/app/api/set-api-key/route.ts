import {NextRequest, NextResponse} from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const {user_id, api_key} = body;

        // Validate required fields
        if (!user_id || !api_key) {
            return NextResponse.json(
                {detail: 'User ID and API key are required'},
                {status: 400}
            );
        }

        // Make the actual request to your external API
        const response = await fetch('http://localhost:1235/set_api_key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: user_id.trim(),
                api_key: api_key.trim()
            })
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(
                {detail: data.detail || data.message || 'Failed to set API key'},
                {status: response.status}
            );
        }

        // Return success response
        return NextResponse.json(
            {message: 'API key set successfully', data},
            {status: 200}
        );

    } catch (error) {
        console.error('API route error:', error);
        return NextResponse.json(
            {detail: 'Internal server error'},
            {status: 500}
        );
    }
}
